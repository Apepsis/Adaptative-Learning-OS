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


async def _subject(client: AsyncClient, name: str = "Physics") -> str:
    return (await client.post("/v1/subjects", json={"name": name})).json()["id"]


async def _mcq_question(client: AsyncClient, subject_id: str) -> dict:
    response = await client.post(
        f"/v1/subjects/{subject_id}/questions",
        json={
            "question_type": "mcq",
            "stem": "What is the SI unit of force?",
            "options": [
                {"id": "a", "text": "Joule"},
                {"id": "b", "text": "Newton"},
                {"id": "c", "text": "Watt"},
                {"id": "d", "text": "Pascal"},
            ],
            "correct_option_id": "b",
            "hints": ["It's named after a physicist.", "Also a unit of weight."],
        },
    )
    assert response.status_code == 201
    return response.json()


async def _numeric_question(client: AsyncClient, subject_id: str) -> dict:
    response = await client.post(
        f"/v1/subjects/{subject_id}/questions",
        json={
            "question_type": "numeric",
            "stem": "What is 2 + 2?",
            "numeric_answer": 4,
            "numeric_tolerance": 0,
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_create_question_validates_mcq_shape(client: AsyncClient) -> None:
    subject_id = await _subject(client)

    missing_correct = await client.post(
        f"/v1/subjects/{subject_id}/questions",
        json={
            "question_type": "mcq",
            "stem": "?",
            "options": [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}],
            "correct_option_id": "z",  # doesn't match any option
        },
    )
    assert missing_correct.status_code == 422

    too_few_options = await client.post(
        f"/v1/subjects/{subject_id}/questions",
        json={"question_type": "mcq", "stem": "?", "options": [{"id": "a", "text": "x"}], "correct_option_id": "a"},
    )
    assert too_few_options.status_code == 422


@pytest.mark.asyncio
async def test_create_question_validates_numeric_and_short_answer_shape(client: AsyncClient) -> None:
    subject_id = await _subject(client)

    no_answer = await client.post(
        f"/v1/subjects/{subject_id}/questions", json={"question_type": "numeric", "stem": "?"}
    )
    assert no_answer.status_code == 422

    no_sample = await client.post(
        f"/v1/subjects/{subject_id}/questions", json={"question_type": "short_answer", "stem": "?"}
    )
    assert no_sample.status_code == 422


@pytest.mark.asyncio
async def test_practice_session_with_no_questions_is_a_clear_422(client: AsyncClient) -> None:
    subject_id = await _subject(client)
    response = await client.post(f"/v1/subjects/{subject_id}/practice/sessions", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_practice_session_returns_first_question_without_leaking_the_answer(
    client: AsyncClient,
) -> None:
    subject_id = await _subject(client)
    await _mcq_question(client, subject_id)

    response = await client.post(f"/v1/subjects/{subject_id}/practice/sessions", json={"question_count": 5})

    assert response.status_code == 201
    body = response.json()
    assert body["session"]["total_questions"] == 1
    assert body["question"] is not None
    assert body["question"]["hint_count"] == 2
    assert "correct_option_id" not in body["question"]
    assert "answer" not in str(body["question"]).lower()


@pytest.mark.asyncio
async def test_correct_mcq_attempt_is_graded_without_error_classification(
    client: AsyncClient, fake_generation_provider: FakeGenerationProvider
) -> None:
    subject_id = await _subject(client)
    question = await _mcq_question(client, subject_id)

    response = await client.post(
        "/v1/attempts",
        json={"question_id": question["id"], "raw_answer": {"option_id": "b"}, "elapsed_ms": 4000},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["correctness"] == "correct"
    assert body["score"] == 1.0
    assert body["errors"] == []
    assert body["correct_option_id"] == "b"  # revealed now that it's answered
    # Grading MCQ never needs the LLM; classification is skipped when correct.
    assert fake_generation_provider.structured_calls == []


@pytest.mark.asyncio
async def test_incorrect_mcq_attempt_triggers_error_classification(
    client: AsyncClient, fake_generation_provider: FakeGenerationProvider
) -> None:
    from app.modules.practice.service import _ErrorClassification

    subject_id = await _subject(client)
    question = await _mcq_question(client, subject_id)
    fake_generation_provider.structured_response = _ErrorClassification(
        error_type="FORMULA_RECALL", explanation="Confused the unit of energy with the unit of force."
    )

    response = await client.post(
        "/v1/attempts", json={"question_id": question["id"], "raw_answer": {"option_id": "a"}}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["correctness"] == "incorrect"
    assert len(body["errors"]) == 1
    assert body["errors"][0]["error_type"] == "FORMULA_RECALL"
    assert len(fake_generation_provider.structured_calls) == 1


@pytest.mark.asyncio
async def test_short_answer_attempt_uses_llm_grading_and_feedback(
    client: AsyncClient, fake_generation_provider: FakeGenerationProvider
) -> None:
    from app.modules.practice.service import _ShortAnswerGrade

    subject_id = await _subject(client)
    question_response = await client.post(
        f"/v1/subjects/{subject_id}/questions",
        json={
            "question_type": "short_answer",
            "stem": "Why does a heavier object not fall faster than a lighter one (ignoring air resistance)?",
            "sample_answer": "Because acceleration due to gravity is independent of mass.",
        },
    )
    question = question_response.json()

    fake_generation_provider.structured_response = _ShortAnswerGrade(
        correctness="partial",
        score=0.5,
        feedback="You mentioned gravity but didn't explain why mass cancels out.",
        error_type="INCOMPLETE_JUSTIFICATION",
        error_explanation="Missing the F=ma cancellation argument.",
    )

    response = await client.post(
        "/v1/attempts",
        json={"question_id": question["id"], "raw_answer": {"text": "Gravity pulls them the same."}},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["correctness"] == "partial"
    assert body["score"] == 0.5
    assert body["feedback"] == "You mentioned gravity but didn't explain why mass cancels out."
    assert body["errors"][0]["error_type"] == "INCOMPLETE_JUSTIFICATION"
    # Short-answer grading gets error classification for free in the same
    # call — no second structured call needed.
    assert len(fake_generation_provider.structured_calls) == 1


@pytest.mark.asyncio
async def test_revealing_the_solution_counts_as_incorrect_and_skips_grading(
    client: AsyncClient, fake_generation_provider: FakeGenerationProvider
) -> None:
    from app.modules.practice.service import _ErrorClassification

    subject_id = await _subject(client)
    question = await _numeric_question(client, subject_id)
    fake_generation_provider.structured_response = _ErrorClassification(
        error_type="CARELESS", explanation="Solution was revealed before attempting."
    )

    response = await client.post(
        "/v1/attempts",
        json={"question_id": question["id"], "raw_answer": {"value": 4}, "solution_revealed": True},
    )

    assert response.status_code == 201
    assert response.json()["correctness"] == "incorrect"
    assert response.json()["score"] == 0.0


@pytest.mark.asyncio
async def test_session_progresses_and_completes(client: AsyncClient) -> None:
    subject_id = await _subject(client)
    q1 = await _mcq_question(client, subject_id)
    q2 = await _numeric_question(client, subject_id)

    created = await client.post(f"/v1/subjects/{subject_id}/practice/sessions", json={"question_count": 2})
    session_id = created.json()["session"]["id"]
    first_question_id = created.json()["question"]["id"]
    assert first_question_id in (q1["id"], q2["id"])

    remaining_id = q2["id"] if first_question_id == q1["id"] else q1["id"]
    remaining_answer = (
        {"option_id": "b"} if remaining_id == q1["id"] else {"value": 4}
    )
    first_answer = {"option_id": "b"} if first_question_id == q1["id"] else {"value": 4}

    await client.post(
        "/v1/attempts",
        json={"question_id": first_question_id, "session_id": session_id, "raw_answer": first_answer},
    )

    progressed = await client.get(f"/v1/subjects/{subject_id}/practice/sessions/{session_id}/current")
    assert progressed.json()["session"]["current_index"] == 1
    assert progressed.json()["question"]["id"] == remaining_id

    await client.post(
        "/v1/attempts",
        json={"question_id": remaining_id, "session_id": session_id, "raw_answer": remaining_answer},
    )

    finished = await client.get(f"/v1/subjects/{subject_id}/practice/sessions/{session_id}/current")
    assert finished.json()["session"]["current_index"] == 2
    assert finished.json()["session"]["completed_at"] is not None
    assert finished.json()["question"] is None


@pytest.mark.asyncio
async def test_hints_are_revealed_one_at_a_time(client: AsyncClient) -> None:
    subject_id = await _subject(client)
    question = await _mcq_question(client, subject_id)

    first = await client.get(f"/v1/subjects/{subject_id}/questions/{question['id']}/hints/0")
    assert first.json() == {
        "hint_text": "It's named after a physicist.",
        "hints_used": 1,
        "hints_remaining": 1,
    }

    second = await client.get(f"/v1/subjects/{subject_id}/questions/{question['id']}/hints/1")
    assert second.json()["hint_text"] == "Also a unit of weight."
    assert second.json()["hints_remaining"] == 0

    beyond = await client.get(f"/v1/subjects/{subject_id}/questions/{question['id']}/hints/5")
    assert beyond.json()["hint_text"] is None


@pytest.mark.asyncio
async def test_questions_and_attempts_are_scoped_to_the_owning_user(
    client: AsyncClient, other_user
) -> None:
    from app.core.security import get_current_user
    from app.modules.identity.models import User

    subject_id = await _subject(client)
    question = await _mcq_question(client, subject_id)

    previous_override = fastapi_app.dependency_overrides[get_current_user]

    async def _other_user_override() -> User:
        return other_user

    fastapi_app.dependency_overrides[get_current_user] = _other_user_override
    try:
        response = await client.get(f"/v1/subjects/{subject_id}/questions")
        attempt_response = await client.post(
            "/v1/attempts", json={"question_id": question["id"], "raw_answer": {"option_id": "b"}}
        )
    finally:
        fastapi_app.dependency_overrides[get_current_user] = previous_override

    assert response.status_code == 404  # subject not owned by other_user
    assert attempt_response.status_code == 404  # question's subject not owned either


async def _subject_with_concept(
    client: AsyncClient, session: AsyncSession, fake: FakeGenerationProvider
) -> tuple[str, str]:
    """Returns (subject_id, concept_id) with one ingested source and one
    built concept — the setup generate_questions needs for evidence."""
    subject_id = await _subject(client)

    with FIXTURE_PATH.open("rb") as fh:
        files = {"file": ("kinematics.pdf", fh, "application/pdf")}
        data = {"subject_id": subject_id}
        upload = await client.post("/v1/sources/upload", files=files, data=data)
    source_id = upload.json()["id"]
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
                name="Time of flight",
                definition="The total time a projectile remains in the air.",
                concept_type="concept",
                evidence_indices=[0],
            )
        ]
    )
    await client.post(f"/v1/subjects/{subject_id}/curriculum/build")
    concepts = (await client.get(f"/v1/subjects/{subject_id}/concepts")).json()["items"]
    return subject_id, concepts[0]["id"]


@pytest.mark.asyncio
async def test_structurally_invalid_generated_question_is_quarantined_not_verified(
    client: AsyncClient, db_session: AsyncSession, fake_generation_provider: FakeGenerationProvider
) -> None:
    from app.modules.practice.service import _GeneratedMCQ, _GeneratedMCQBatch

    subject_id, concept_id = await _subject_with_concept(client, db_session, fake_generation_provider)

    # correct_option_id references an option that doesn't exist — exactly
    # the kind of malformed output the structural check must catch.
    fake_generation_provider.structured_response = _GeneratedMCQBatch(
        questions=[
            _GeneratedMCQ(
                stem="Broken question",
                options=[{"id": "a", "text": "x"}, {"id": "b", "text": "y"}],
                correct_option_id="z",
                solution_text="n/a",
            )
        ]
    )

    generated = await client.post(
        f"/v1/subjects/{subject_id}/questions/generate",
        json={"concept_id": concept_id, "question_type": "mcq", "count": 1},
    )
    assert generated.status_code == 201
    question = generated.json()["items"][0]
    assert question["verification_state"] == "quarantined"

    # Quarantined questions are persisted for review, but must never be
    # selectable into an actual practice session.
    session_response = await client.post(
        f"/v1/subjects/{subject_id}/practice/sessions", json={"question_count": 5}
    )
    assert session_response.status_code == 422
