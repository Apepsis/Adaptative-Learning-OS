import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.factory import get_embedding_provider
from app.ai.providers.factory import get_generation_provider
from app.core.config import get_settings
from app.main import app as fastapi_app
from app.modules.curriculum.schemas import ConceptExtractionResult, ExtractedConcept, ExtractedEdge
from app.modules.ingestion.parsers.pypdf_parser import PyPdfParser
from app.modules.ingestion.service import ingest_source
from app.storage.client import get_storage_client
from app.tests.fakes import FakeEmbeddingProvider, FakeGenerationProvider

FIXTURE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "kinematics.pdf"


@pytest.fixture
def fake_generation_provider() -> Generator[FakeGenerationProvider]:
    fake = FakeGenerationProvider()
    fastapi_app.dependency_overrides[get_generation_provider] = lambda: fake
    fastapi_app.dependency_overrides[get_embedding_provider] = lambda: FakeEmbeddingProvider()
    try:
        yield fake
    finally:
        fastapi_app.dependency_overrides.pop(get_generation_provider, None)
        fastapi_app.dependency_overrides.pop(get_embedding_provider, None)


async def _subject_with_ingested_source(client: AsyncClient, session: AsyncSession) -> str:
    subject = (await client.post("/v1/subjects", json={"name": "Physics"})).json()

    with FIXTURE_PATH.open("rb") as fh:
        files = {"file": ("kinematics.pdf", fh, "application/pdf")}
        data = {"subject_id": subject["id"]}
        response = await client.post("/v1/sources/upload", files=files, data=data)
    assert response.status_code == 202
    source_id = response.json()["id"]

    await ingest_source(
        session,
        get_storage_client(),
        get_settings(),
        PyPdfParser(),
        FakeEmbeddingProvider(),
        source_id=uuid.UUID(source_id),
    )
    return subject["id"]


def _two_concept_extraction() -> ConceptExtractionResult:
    return ConceptExtractionResult(
        concepts=[
            ExtractedConcept(
                name="Projectile motion",
                definition="Motion of an object launched into the air, subject only to gravity.",
                concept_type="topic",
                aliases=["2D projectile motion"],
                evidence_indices=[0],
                edges=[],
            ),
            ExtractedConcept(
                name="Range of a projectile",
                definition="The horizontal distance a projectile travels before landing.",
                concept_type="subtopic",
                evidence_indices=[0],
                edges=[ExtractedEdge(target_concept_name="Projectile motion", relation="PART_OF")],
            ),
        ]
    )


@pytest.mark.asyncio
async def test_build_curriculum_creates_concepts_and_edges(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject_id = await _subject_with_ingested_source(client, db_session)
    fake_generation_provider.structured_response = _two_concept_extraction()

    response = await client.post(f"/v1/subjects/{subject_id}/curriculum/build")

    assert response.status_code == 201
    body = response.json()
    assert body["concepts_created"] == 2
    assert body["edges_created"] == 1
    assert body["chunks_considered"] > 0

    listed = await client.get(f"/v1/subjects/{subject_id}/concepts")
    names = {c["canonical_name"] for c in listed.json()["items"]}
    assert names == {"Projectile motion", "Range of a projectile"}


@pytest.mark.asyncio
async def test_build_curriculum_populates_evidence_and_edge_detail(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject_id = await _subject_with_ingested_source(client, db_session)
    fake_generation_provider.structured_response = _two_concept_extraction()
    await client.post(f"/v1/subjects/{subject_id}/curriculum/build")

    listed = (await client.get(f"/v1/subjects/{subject_id}/concepts")).json()["items"]
    subtopic = next(c for c in listed if c["canonical_name"] == "Range of a projectile")

    detail = await client.get(f"/v1/subjects/{subject_id}/concepts/{subtopic['id']}")
    body = detail.json()
    assert len(body["evidence"]) > 0
    assert body["evidence"][0]["text"]  # real excerpt text, not just an id
    assert len(body["outgoing_edges"]) == 1
    assert body["outgoing_edges"][0]["relation"] == "PART_OF"


@pytest.mark.asyncio
async def test_rerunning_build_updates_instead_of_duplicating(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject_id = await _subject_with_ingested_source(client, db_session)
    fake_generation_provider.structured_response = _two_concept_extraction()

    first = await client.post(f"/v1/subjects/{subject_id}/curriculum/build")
    assert first.json()["concepts_created"] == 2

    second = await client.post(f"/v1/subjects/{subject_id}/curriculum/build")
    assert second.json()["concepts_created"] == 0
    assert second.json()["concepts_updated"] == 2

    listed = await client.get(f"/v1/subjects/{subject_id}/concepts")
    assert listed.json()["total"] == 2  # still just two concepts, not four


@pytest.mark.asyncio
async def test_cyclic_edge_is_rejected_not_silently_corrupted(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject_id = await _subject_with_ingested_source(client, db_session)
    fake_generation_provider.structured_response = ConceptExtractionResult(
        concepts=[
            ExtractedConcept(
                name="A",
                definition="First.",
                evidence_indices=[0],
                edges=[ExtractedEdge(target_concept_name="B", relation="PREREQUISITE_OF")],
            ),
            ExtractedConcept(
                name="B",
                definition="Second.",
                evidence_indices=[0],
                edges=[ExtractedEdge(target_concept_name="A", relation="PREREQUISITE_OF")],
            ),
        ]
    )

    response = await client.post(f"/v1/subjects/{subject_id}/curriculum/build")
    body = response.json()
    assert body["edges_created"] == 1
    assert body["edges_skipped_cycle"] == 1


@pytest.mark.asyncio
async def test_build_without_any_processed_source_is_a_clear_422(
    client: AsyncClient, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject = (await client.post("/v1/subjects", json={"name": "Empty subject"})).json()

    response = await client.post(f"/v1/subjects/{subject['id']}/curriculum/build")

    assert response.status_code == 422
    assert fake_generation_provider.structured_calls == []  # never even called the LLM


@pytest.mark.asyncio
async def test_merge_concepts_reassigns_edges_and_evidence(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject_id = await _subject_with_ingested_source(client, db_session)
    fake_generation_provider.structured_response = _two_concept_extraction()
    await client.post(f"/v1/subjects/{subject_id}/curriculum/build")

    listed = (await client.get(f"/v1/subjects/{subject_id}/concepts")).json()["items"]
    primary = next(c for c in listed if c["canonical_name"] == "Projectile motion")
    absorbed = next(c for c in listed if c["canonical_name"] == "Range of a projectile")

    merge_response = await client.post(
        f"/v1/subjects/{subject_id}/concepts/{primary['id']}/merge",
        json={"absorb_concept_id": absorbed["id"]},
    )
    assert merge_response.status_code == 200

    remaining = await client.get(f"/v1/subjects/{subject_id}/concepts")
    assert remaining.json()["total"] == 1

    # The absorbed concept's PART_OF edge pointed at the primary, which
    # would be a self-loop after merging — reassign_edges must drop it,
    # not leave a dangling/self-referential edge.
    detail = await client.get(f"/v1/subjects/{subject_id}/concepts/{primary['id']}")
    assert detail.json()["outgoing_edges"] == []
    assert detail.json()["incoming_edges"] == []


@pytest.mark.asyncio
async def test_curriculum_endpoints_404_for_a_subject_you_dont_own(
    client: AsyncClient, other_user, fake_generation_provider: FakeGenerationProvider
) -> None:
    from app.core.security import get_current_user
    from app.modules.identity.models import User

    subject = (await client.post("/v1/subjects", json={"name": "Private"})).json()

    previous_override = fastapi_app.dependency_overrides[get_current_user]

    async def _other_user_override() -> User:
        return other_user

    fastapi_app.dependency_overrides[get_current_user] = _other_user_override
    try:
        response = await client.get(f"/v1/subjects/{subject['id']}/concepts")
    finally:
        fastapi_app.dependency_overrides[get_current_user] = previous_override

    assert response.status_code == 404
