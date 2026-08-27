import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.curriculum.models import Concept
from app.modules.curriculum.repository import CurriculumRepository
from app.modules.mastery.bkt import BOOTSTRAP_PRIOR_MASTERY
from app.tests.fakes import FakeGenerationProvider
from app.tests.modules.practice.test_practice_flow import (
    _mcq_question,
    _subject,
    fake_generation_provider,
)

__all__ = ["fake_generation_provider"]  # re-exported fixture, used implicitly by pytest


async def _concept(db_session: AsyncSession, subject_id: str, name: str = "Kinematics") -> str:
    concept = await CurriculumRepository(db_session).create_concept(
        Concept(subject_id=uuid.UUID(subject_id), canonical_name=name, slug=name.lower(), concept_type="concept")
    )
    await db_session.commit()
    return str(concept.id)


async def _mcq_question_with_concept(client: AsyncClient, subject_id: str, concept_id: str) -> dict:
    response = await client.post(
        f"/v1/subjects/{subject_id}/questions",
        json={
            "concept_id": concept_id,
            "question_type": "mcq",
            "stem": "What is the SI unit of force?",
            "options": [
                {"id": "a", "text": "Joule"},
                {"id": "b", "text": "Newton"},
            ],
            "correct_option_id": "b",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_correct_attempt_creates_and_updates_concept_mastery(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    subject_id = await _subject(client)
    concept_id = await _concept(db_session, subject_id)
    question = await _mcq_question_with_concept(client, subject_id, concept_id)

    response = await client.post(
        "/v1/attempts", json={"question_id": question["id"], "raw_answer": {"option_id": "b"}}
    )
    assert response.status_code == 201

    mastery = await client.get(f"/v1/subjects/{subject_id}/mastery/concepts/{concept_id}")
    assert mastery.status_code == 200
    body = mastery.json()
    assert body["p_mastery"] > BOOTSTRAP_PRIOR_MASTERY
    assert body["observation_count"] == 1
    assert body["distinct_question_count"] == 1
    assert body["recent_accuracy"] == 1.0


@pytest.mark.asyncio
async def test_question_without_concept_never_creates_a_mastery_row(client: AsyncClient) -> None:
    subject_id = await _subject(client)
    question = await _mcq_question(client, subject_id)  # no concept_id

    await client.post("/v1/attempts", json={"question_id": question["id"], "raw_answer": {"option_id": "b"}})

    listing = await client.get(f"/v1/subjects/{subject_id}/mastery")
    assert listing.json()["items"] == []


@pytest.mark.asyncio
async def test_repeated_errors_on_two_questions_confirm_a_misconception(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    from app.modules.practice.service import _ErrorClassification

    subject_id = await _subject(client)
    concept_id = await _concept(db_session, subject_id)
    q1 = await _mcq_question_with_concept(client, subject_id, concept_id)
    q2 = await _mcq_question_with_concept(client, subject_id, concept_id)
    fake_generation_provider.structured_response = _ErrorClassification(
        error_type="VECTOR_COMPONENT", explanation="Mixed up components."
    )

    for question_id in (q1["id"], q1["id"], q1["id"], q2["id"], q2["id"]):
        result = await client.post(
            "/v1/attempts", json={"question_id": question_id, "raw_answer": {"option_id": "a"}}
        )
        assert result.status_code == 201

    patterns = (await client.get(f"/v1/subjects/{subject_id}/mastery/patterns")).json()["items"]
    assert len(patterns) == 1
    assert patterns[0]["error_type"] == "VECTOR_COMPONENT"
    assert patterns[0]["status"] == "confirmed"
    assert patterns[0]["event_count"] == 5
    assert patterns[0]["distinct_question_count"] == 2


@pytest.mark.asyncio
async def test_repeated_errors_on_one_question_stay_a_candidate(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    from app.modules.practice.service import _ErrorClassification

    subject_id = await _subject(client)
    concept_id = await _concept(db_session, subject_id)
    question = await _mcq_question_with_concept(client, subject_id, concept_id)
    fake_generation_provider.structured_response = _ErrorClassification(
        error_type="SIGN", explanation="Dropped a negative sign."
    )

    for _ in range(3):
        await client.post("/v1/attempts", json={"question_id": question["id"], "raw_answer": {"option_id": "a"}})

    patterns = (await client.get(f"/v1/subjects/{subject_id}/mastery/patterns")).json()["items"]
    assert len(patterns) == 1
    assert patterns[0]["status"] == "candidate"


@pytest.mark.asyncio
async def test_low_mastery_concept_surfaces_as_a_weakness(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    from app.modules.practice.service import _ErrorClassification

    subject_id = await _subject(client)
    concept_id = await _concept(db_session, subject_id)
    question = await _mcq_question_with_concept(client, subject_id, concept_id)
    fake_generation_provider.structured_response = _ErrorClassification(
        error_type="CARELESS", explanation="n/a"
    )

    for _ in range(3):
        await client.post("/v1/attempts", json={"question_id": question["id"], "raw_answer": {"option_id": "a"}})

    weaknesses = (await client.get(f"/v1/subjects/{subject_id}/mastery/weaknesses")).json()["items"]
    assert len(weaknesses) == 1
    assert weaknesses[0]["concept_id"] == concept_id


@pytest.mark.asyncio
async def test_mastery_is_scoped_to_the_owning_user(
    client: AsyncClient, db_session: AsyncSession, other_user
) -> None:
    from app.core.security import get_current_user
    from app.main import app as fastapi_app
    from app.modules.identity.models import User

    subject_id = await _subject(client)
    concept_id = await _concept(db_session, subject_id)
    question = await _mcq_question_with_concept(client, subject_id, concept_id)
    await client.post("/v1/attempts", json={"question_id": question["id"], "raw_answer": {"option_id": "b"}})

    previous_override = fastapi_app.dependency_overrides[get_current_user]

    async def _other_user_override() -> User:
        return other_user

    fastapi_app.dependency_overrides[get_current_user] = _other_user_override
    try:
        response = await client.get(f"/v1/subjects/{subject_id}/mastery")
    finally:
        fastapi_app.dependency_overrides[get_current_user] = previous_override

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_flashcard_review_schedules_it_out_of_the_due_list(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    subject_id = await _subject(client)
    concept_id = await _concept(db_session, subject_id)
    created = await client.post(
        f"/v1/subjects/{subject_id}/flashcards",
        json={"concept_id": concept_id, "front": "What is F=ma?", "back": "Newton's second law."},
    )
    flashcard_id = created.json()["id"]

    due_before = (await client.get(f"/v1/subjects/{subject_id}/flashcards/due")).json()["items"]
    assert any(c["id"] == flashcard_id for c in due_before)

    review = await client.post(
        f"/v1/subjects/{subject_id}/flashcards/{flashcard_id}/review", json={"rating": "good", "response_ms": 3000}
    )
    assert review.status_code == 201
    body = review.json()
    assert body["stability"] is not None
    assert body["state"] == "learning"

    due_after = (await client.get(f"/v1/subjects/{subject_id}/flashcards/due")).json()["items"]
    assert not any(c["id"] == flashcard_id for c in due_after)


@pytest.mark.asyncio
async def test_flashcard_review_rejects_unknown_rating(client: AsyncClient, db_session: AsyncSession) -> None:
    subject_id = await _subject(client)
    concept_id = await _concept(db_session, subject_id)
    created = await client.post(
        f"/v1/subjects/{subject_id}/flashcards",
        json={"concept_id": concept_id, "front": "Q", "back": "A"},
    )
    flashcard_id = created.json()["id"]

    response = await client.post(
        f"/v1/subjects/{subject_id}/flashcards/{flashcard_id}/review", json={"rating": "perfect"}
    )
    assert response.status_code == 422
