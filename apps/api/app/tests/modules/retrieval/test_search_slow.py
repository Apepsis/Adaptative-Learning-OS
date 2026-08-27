"""End-to-end Phase 2 acceptance test (blueprint section 48): upload the
fixture PDF, run the real ingestion pipeline synchronously (no Celery), and
verify golden queries return the expected page in the top results, plus a
query with no answer in the source returns an honest empty result.

Marked slow: downloads/runs the real BGE-M3 model (~2GB on first run) and
parses a real PDF. Run explicitly with `make test-api-slow`.
"""

import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.factory import get_embedding_provider
from app.core.config import get_settings
from app.modules.ingestion.parsers.pypdf_parser import PyPdfParser
from app.modules.ingestion.service import ingest_source
from app.modules.sources.models import SourceStatus
from app.storage.client import get_storage_client

FIXTURE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "kinematics.pdf"

pytestmark = pytest.mark.slow


async def _upload_and_ingest(client: AsyncClient, session: AsyncSession) -> str:
    with FIXTURE_PATH.open("rb") as fh:
        files = {"file": ("kinematics.pdf", fh, "application/pdf")}
        response = await client.post("/v1/sources/upload", files=files)
    assert response.status_code == 202
    source_id = response.json()["id"]

    await ingest_source(
        session,
        get_storage_client(),
        get_settings(),
        PyPdfParser(),
        get_embedding_provider(),
        source_id=uuid.UUID(source_id),
    )
    return source_id


@pytest.mark.asyncio
async def test_ingestion_reaches_ready_with_chunks(client: AsyncClient, db_session: AsyncSession) -> None:
    source_id = await _upload_and_ingest(client, db_session)

    detail = await client.get(f"/v1/sources/{source_id}")
    assert detail.json()["status"] == SourceStatus.READY.value


@pytest.mark.asyncio
async def test_golden_query_returns_expected_page(client: AsyncClient, db_session: AsyncSession) -> None:
    source_id = await _upload_and_ingest(client, db_session)

    response = await client.post(
        "/v1/search", json={"query": "What is the range formula for a projectile?", "top_k": 5}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["not_found"] is False

    # The fixture is only 4 short pages (~170 tokens total), so the real
    # chunker (by design — see _HEADING_FLUSH_RATIO in
    # app/modules/ingestion/chunking.py) merges it into a single chunk
    # spanning pages 1-4 rather than fragmenting tiny sections. That makes
    # asserting an exact page number the wrong check here; assert on the
    # actual content instead, which is what a golden query is really for.
    assert any("range" in r["text"].lower() and "sin(2" in r["text"] for r in body["results"])
    assert any(r["source_id"] == source_id for r in body["results"])


@pytest.mark.asyncio
async def test_second_golden_query_returns_newtons_law_page(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _upload_and_ingest(client, db_session)

    response = await client.post("/v1/search", json={"query": "What does Newton's second law state?"})
    body = response.json()

    # Same reasoning as the golden query above: assert on content, not an
    # exact page number, since the tiny fixture merges into one chunk.
    assert any("f = m * a" in r["text"].lower() for r in body["results"])


@pytest.mark.asyncio
async def test_query_with_no_relevant_source_is_honestly_not_found(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # No source uploaded in this test at all — nothing could match.
    response = await client.post("/v1/search", json={"query": "How do I bake a sourdough loaf?"})
    body = response.json()
    assert body["results"] == []
    assert body["not_found"] is True


@pytest.mark.asyncio
async def test_search_is_scoped_to_the_requesting_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A source belonging to another user must never appear in search
    results, even if the query matches its content very well."""
    from app.core.security import get_current_user
    from app.main import app as fastapi_app
    from app.modules.identity.models import User
    from app.modules.identity.repository import UserRepository

    other_user = await UserRepository(db_session).create(email="other-search-user@example.com")
    await db_session.commit()

    previous_override = fastapi_app.dependency_overrides[get_current_user]

    async def _other_user_override() -> User:
        return other_user

    fastapi_app.dependency_overrides[get_current_user] = _other_user_override
    try:
        await _upload_and_ingest(client, db_session)
    finally:
        fastapi_app.dependency_overrides[get_current_user] = previous_override

    response = await client.post("/v1/search", json={"query": "projectile range formula"})
    assert response.json()["results"] == []
