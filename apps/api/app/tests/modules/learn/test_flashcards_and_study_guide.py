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
from app.modules.curriculum.schemas import ConceptExtractionResult, ExtractedConcept
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


async def _subject_with_concepts(client: AsyncClient, session: AsyncSession, fake: FakeGenerationProvider) -> str:
    subject = (await client.post("/v1/subjects", json={"name": "Physics"})).json()

    with FIXTURE_PATH.open("rb") as fh:
        files = {"file": ("kinematics.pdf", fh, "application/pdf")}
        data = {"subject_id": subject["id"]}
        response = await client.post("/v1/sources/upload", files=files, data=data)
    source_id = response.json()["id"]
    await ingest_source(
        session,
        get_storage_client(),
        get_settings(),
        PyPdfParser(),
        FakeEmbeddingProvider(),
        source_id=uuid.UUID(source_id),
    )

    fake.structured_response = ConceptExtractionResult(
        concepts=[
            ExtractedConcept(
                name="Projectile motion",
                definition="Motion of an object launched into the air, subject only to gravity.",
                concept_type="topic",
                evidence_indices=[0],
            ),
            ExtractedConcept(
                name="Time of flight",
                definition="The total time a projectile remains in the air.",
                concept_type="concept",
                evidence_indices=[0],
            ),
        ]
    )
    await client.post(f"/v1/subjects/{subject['id']}/curriculum/build")
    return subject["id"]


@pytest.mark.asyncio
async def test_generate_flashcards_covers_concepts_but_not_topics(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject_id = await _subject_with_concepts(client, db_session, fake_generation_provider)

    response = await client.post(f"/v1/subjects/{subject_id}/flashcards/generate")

    assert response.status_code == 201
    assert response.json()["created"] == 1  # only "Time of flight" (concept), not "Projectile motion" (topic)

    listed = await client.get(f"/v1/subjects/{subject_id}/flashcards")
    cards = listed.json()["items"]
    assert len(cards) == 1
    assert cards[0]["front"] == "What is Time of flight?"
    assert cards[0]["source_grounded"] is True


@pytest.mark.asyncio
async def test_generating_flashcards_twice_does_not_duplicate(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject_id = await _subject_with_concepts(client, db_session, fake_generation_provider)

    first = await client.post(f"/v1/subjects/{subject_id}/flashcards/generate")
    assert first.json()["created"] == 1

    second = await client.post(f"/v1/subjects/{subject_id}/flashcards/generate")
    assert second.json()["created"] == 0
    assert second.json()["skipped_existing"] == 1

    listed = await client.get(f"/v1/subjects/{subject_id}/flashcards")
    assert listed.json()["total"] == 1


@pytest.mark.asyncio
async def test_manual_flashcard_crud(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject_id = await _subject_with_concepts(client, db_session, fake_generation_provider)
    concepts = (await client.get(f"/v1/subjects/{subject_id}/concepts")).json()["items"]
    concept_id = concepts[0]["id"]

    created = await client.post(
        f"/v1/subjects/{subject_id}/flashcards",
        json={"concept_id": concept_id, "front": "Custom front", "back": "Custom back"},
    )
    assert created.status_code == 201
    card = created.json()
    assert card["source_grounded"] is False

    updated = await client.patch(
        f"/v1/subjects/{subject_id}/flashcards/{card['id']}", json={"back": "Updated back"}
    )
    assert updated.json()["back"] == "Updated back"
    assert updated.json()["front"] == "Custom front"

    deleted = await client.delete(f"/v1/subjects/{subject_id}/flashcards/{card['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/v1/subjects/{subject_id}/flashcards")).json()["items"] == []


@pytest.mark.asyncio
async def test_study_guide_generation_and_retrieval(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject_id = await _subject_with_concepts(client, db_session, fake_generation_provider)
    fake_generation_provider.response = "## Projectile Motion\n\nA thorough guide..."

    generated = await client.post(f"/v1/subjects/{subject_id}/study-guide/generate")
    assert generated.status_code == 201
    assert generated.json()["content"] == fake_generation_provider.response

    # The prompt actually included the extracted concepts, not a generic ask.
    call = fake_generation_provider.calls[-1]
    assert "Time of flight" in call["user_message"]
    assert "Projectile motion" in call["user_message"]

    fetched = await client.get(f"/v1/subjects/{subject_id}/study-guide")
    assert fetched.status_code == 200
    assert fetched.json()["content"] == fake_generation_provider.response


@pytest.mark.asyncio
async def test_study_guide_regeneration_overwrites_not_duplicates(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject_id = await _subject_with_concepts(client, db_session, fake_generation_provider)

    fake_generation_provider.response = "first version"
    await client.post(f"/v1/subjects/{subject_id}/study-guide/generate")

    fake_generation_provider.response = "second version"
    await client.post(f"/v1/subjects/{subject_id}/study-guide/generate")

    fetched = await client.get(f"/v1/subjects/{subject_id}/study-guide")
    assert fetched.json()["content"] == "second version"


@pytest.mark.asyncio
async def test_study_guide_without_concepts_is_a_clear_422(
    client: AsyncClient, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject = (await client.post("/v1/subjects", json={"name": "Empty subject"})).json()

    response = await client.post(f"/v1/subjects/{subject['id']}/study-guide/generate")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_study_guide_404s_before_first_generation(
    client: AsyncClient, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject = (await client.post("/v1/subjects", json={"name": "Fresh subject"})).json()

    response = await client.get(f"/v1/subjects/{subject['id']}/study-guide")

    assert response.status_code == 404
