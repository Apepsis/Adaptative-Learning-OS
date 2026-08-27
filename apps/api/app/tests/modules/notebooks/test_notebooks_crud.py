from unittest.mock import patch

import pytest
from httpx import AsyncClient

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"


async def _upload_source(client: AsyncClient, filename: str = "notes.pdf") -> str:
    files = {"file": (filename, _MINIMAL_PDF, "application/pdf")}
    with patch("app.modules.sources.service.ingest_source_task"):
        response = await client.post("/v1/sources/upload", files=files)
    assert response.status_code == 202
    return response.json()["id"]


async def _create_notebook(client: AsyncClient, title: str = "Physics") -> dict:
    response = await client.post("/v1/notebooks", json={"title": title})
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_create_list_get_delete_notebook(client: AsyncClient) -> None:
    created = await _create_notebook(client, "IB Physics HL")
    assert created["title"] == "IB Physics HL"

    listed = await client.get("/v1/notebooks")
    assert listed.json()["total"] == 1

    detail = await client.get(f"/v1/notebooks/{created['id']}")
    assert detail.status_code == 200

    deleted = await client.delete(f"/v1/notebooks/{created['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/v1/notebooks/{created['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_notebook_not_visible_to_a_different_user(client: AsyncClient, other_user) -> None:
    from app.core.security import get_current_user
    from app.main import app as fastapi_app
    from app.modules.identity.models import User

    notebook = await _create_notebook(client)

    previous_override = fastapi_app.dependency_overrides[get_current_user]

    async def _other_user_override() -> User:
        return other_user

    fastapi_app.dependency_overrides[get_current_user] = _other_user_override
    try:
        response = await client.get(f"/v1/notebooks/{notebook['id']}")
    finally:
        fastapi_app.dependency_overrides[get_current_user] = previous_override

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_list_remove_source(client: AsyncClient) -> None:
    notebook = await _create_notebook(client)
    source_id = await _upload_source(client)

    add_response = await client.post(f"/v1/notebooks/{notebook['id']}/sources", json={"source_id": source_id})
    assert add_response.status_code == 204

    listed = await client.get(f"/v1/notebooks/{notebook['id']}/sources")
    assert [s["source_id"] for s in listed.json()["items"]] == [source_id]

    remove_response = await client.delete(f"/v1/notebooks/{notebook['id']}/sources/{source_id}")
    assert remove_response.status_code == 204
    assert (await client.get(f"/v1/notebooks/{notebook['id']}/sources")).json()["items"] == []


@pytest.mark.asyncio
async def test_adding_the_same_source_twice_conflicts(client: AsyncClient) -> None:
    notebook = await _create_notebook(client)
    source_id = await _upload_source(client)

    await client.post(f"/v1/notebooks/{notebook['id']}/sources", json={"source_id": source_id})
    second = await client.post(f"/v1/notebooks/{notebook['id']}/sources", json={"source_id": source_id})
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_adding_a_nonexistent_source_404s(client: AsyncClient) -> None:
    notebook = await _create_notebook(client)
    fake_source_id = "00000000-0000-0000-0000-000000000000"

    response = await client.post(f"/v1/notebooks/{notebook['id']}/sources", json={"source_id": fake_source_id})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_notes_crud(client: AsyncClient) -> None:
    notebook = await _create_notebook(client)

    created = await client.post(
        f"/v1/notebooks/{notebook['id']}/notes", json={"title": "Key formulas", "content": "R = u^2 sin(2t)/g"}
    )
    assert created.status_code == 201
    note = created.json()

    listed = await client.get(f"/v1/notebooks/{notebook['id']}/notes")
    assert len(listed.json()["items"]) == 1

    updated = await client.patch(
        f"/v1/notebooks/{notebook['id']}/notes/{note['id']}", json={"content": "R = (u^2 * sin(2*theta)) / g"}
    )
    assert updated.status_code == 200
    assert updated.json()["content"] == "R = (u^2 * sin(2*theta)) / g"
    assert updated.json()["title"] == "Key formulas"  # untouched field stays as-is

    deleted = await client.delete(f"/v1/notebooks/{notebook['id']}/notes/{note['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/v1/notebooks/{notebook['id']}/notes")).json()["items"] == []
