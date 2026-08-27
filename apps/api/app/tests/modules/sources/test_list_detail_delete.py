from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_current_user
from app.main import app as fastapi_app
from app.modules.identity.models import User
from app.modules.sources.models import Source
from app.storage.client import get_storage_client

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"


async def _upload(client: AsyncClient, filename: str = "notes.pdf") -> dict:
    files = {"file": (filename, _MINIMAL_PDF, "application/pdf")}
    with patch("app.modules.sources.service.ingest_source_task"):
        response = await client.post("/v1/sources/upload", files=files)
    assert response.status_code == 202
    return response.json()


@pytest.mark.asyncio
async def test_list_and_get_source(client: AsyncClient) -> None:
    created = await _upload(client)

    list_response = await client.get("/v1/sources")
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == created["id"]

    detail_response = await client.get(f"/v1/sources/{created['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["title"] == "notes.pdf"

    status_response = await client.get(f"/v1/sources/{created['id']}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "UPLOADED"


@pytest.mark.asyncio
async def test_source_not_visible_to_a_different_user(client: AsyncClient, other_user: User) -> None:
    created = await _upload(client)

    async def _other_user_override() -> User:
        return other_user

    previous_override = fastapi_app.dependency_overrides[get_current_user]
    fastapi_app.dependency_overrides[get_current_user] = _other_user_override
    try:
        response = await client.get(f"/v1/sources/{created['id']}")
    finally:
        fastapi_app.dependency_overrides[get_current_user] = previous_override

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_source_removes_object_from_storage(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    created = await _upload(client)
    settings = get_settings()

    result = await db_session.execute(select(Source).where(Source.id == created["id"]))
    storage_key = result.scalar_one().storage_key
    assert storage_key is not None

    storage = get_storage_client()
    assert await storage.object_exists(bucket=settings.s3_bucket_originals, key=storage_key)

    delete_response = await client.delete(f"/v1/sources/{created['id']}")
    assert delete_response.status_code == 204

    assert not await storage.object_exists(bucket=settings.s3_bucket_originals, key=storage_key)
    assert (await client.get(f"/v1/sources/{created['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_reprocess_resets_status_and_requeues(client: AsyncClient) -> None:
    created = await _upload(client)

    with patch("app.modules.sources.service.ingest_source_task") as mock_task:
        response = await client.post(f"/v1/sources/{created['id']}/reprocess")

    assert response.status_code == 202
    assert response.json()["status"] == "UPLOADED"
    mock_task.delay.assert_called_once_with(created["id"])


@pytest.mark.asyncio
async def test_delete_nonexistent_source_returns_404(client: AsyncClient) -> None:
    response = await client.delete("/v1/sources/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
