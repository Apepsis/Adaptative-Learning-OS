import uuid
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.factory import get_embedding_provider
from app.ai.providers.factory import get_generation_provider
from app.core.config import get_settings
from app.main import app as fastapi_app
from app.modules.ingestion.parsers.pypdf_parser import PyPdfParser
from app.modules.ingestion.service import ingest_source
from app.storage.client import get_storage_client
from app.tests.modules.notebooks.fakes import FakeEmbeddingProvider, FakeGenerationProvider

FIXTURE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "kinematics.pdf"


@pytest.fixture
def fake_generation_provider() -> Generator[FakeGenerationProvider]:
    fake = FakeGenerationProvider("The range formula is R = (u^2 * sin(2*theta)) / g. [1]")
    fastapi_app.dependency_overrides[get_generation_provider] = lambda: fake
    fastapi_app.dependency_overrides[get_embedding_provider] = lambda: FakeEmbeddingProvider()
    try:
        yield fake
    finally:
        fastapi_app.dependency_overrides.pop(get_generation_provider, None)
        fastapi_app.dependency_overrides.pop(get_embedding_provider, None)


async def _upload_and_ingest_fixture(client: AsyncClient, session: AsyncSession) -> str:
    with FIXTURE_PATH.open("rb") as fh:
        files = {"file": ("kinematics.pdf", fh, "application/pdf")}
        with patch("app.modules.sources.service.ingest_source_task"):
            response = await client.post("/v1/sources/upload", files=files)
    assert response.status_code == 202
    source_id = response.json()["id"]

    # Fast ingestion for the test: real parser (cheap), fake embeddings (no
    # 2GB model download). Real embedding correctness is covered by the
    # `slow`-marked suite instead.
    await ingest_source(
        session,
        get_storage_client(),
        get_settings(),
        PyPdfParser(),
        FakeEmbeddingProvider(),
        source_id=uuid.UUID(source_id),
    )
    return source_id


@pytest.mark.asyncio
async def test_chat_without_any_source_returns_a_clear_message_and_skips_generation(
    client: AsyncClient, fake_generation_provider: FakeGenerationProvider
) -> None:
    notebook = (await client.post("/v1/notebooks", json={"title": "Empty notebook"})).json()

    response = await client.post(f"/v1/notebooks/{notebook['id']}/chat", json={"message": "Anything?"})

    assert response.status_code == 201
    body = response.json()
    assert body["not_found"] is True
    assert body["citations"] == []
    assert fake_generation_provider.calls == []  # never called the LLM — nothing to ground on


@pytest.mark.asyncio
async def test_chat_with_ingested_source_cites_the_right_page_and_persists_history(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    source_id = await _upload_and_ingest_fixture(client, db_session)
    notebook = (await client.post("/v1/notebooks", json={"title": "Physics"})).json()
    await client.post(f"/v1/notebooks/{notebook['id']}/sources", json={"source_id": source_id})

    response = await client.post(
        f"/v1/notebooks/{notebook['id']}/chat",
        json={"message": "What is the range formula for a projectile?"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "assistant"
    assert body["not_found"] is False
    assert body["content"] == fake_generation_provider.response
    assert len(body["citations"]) > 0
    assert all(c["source_id"] == source_id for c in body["citations"])

    # The fake provider actually received the retrieved evidence and the
    # question — not just an empty/placeholder call.
    assert len(fake_generation_provider.calls) == 1
    call = fake_generation_provider.calls[0]
    assert "range" in call["user_message"].lower()
    assert "Question: What is the range formula" in call["user_message"]

    history = await client.get(f"/v1/notebooks/{notebook['id']}/messages")
    roles = [m["role"] for m in history.json()["items"]]
    assert roles == ["user", "assistant"]
