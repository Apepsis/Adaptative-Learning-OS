import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import GenerationProvider
from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationFailedError
from app.modules.curriculum.models import Concept, ConceptEdge
from app.modules.curriculum.repository import CurriculumRepository
from app.modules.learn.models import Flashcard, StudyGuide
from app.modules.learn.repository import LearnRepository
from app.modules.learn.schemas import FlashcardCreate, FlashcardUpdate, GenerateFlashcardsResponse
from app.modules.subjects.repository import SubjectRepository

# Flashcards worth testing recall of are specific, nameable facts —
# broad "topic" groupings don't make good flashcard prompts (blueprint
# section 12's L0 recall is about definitions/symbols/formulas, which
# concept_type "concept"/"skill" map onto much better than "topic" does).
_FLASHCARD_CONCEPT_TYPES = ("concept", "skill")

_STUDY_GUIDE_SYSTEM_INSTRUCTION = """You are writing a study guide for a student, based on a \
structured list of concepts extracted from their own course material.

You will be given the subject's concepts (grouped by type: topics, subtopics, concepts, skills), \
each with a definition, and the relationships between them (e.g. "X PART_OF Y" means X belongs \
under Y; "X PREREQUISITE_OF Y" means X should be understood before Y).

Write a clear, well-organized study guide in Markdown:
- Structure it around the topics and subtopics, in a logical order — respect PREREQUISITE_OF \
relationships where they exist, so foundational ideas come first.
- For each concept, give a clear explanation grounded in its definition — you may elaborate \
slightly for clarity, but do not introduce claims the definitions don't support.
- Use headings (##, ###) and keep it scannable, not a wall of text.
- If there isn't much material yet, write a short guide rather than padding with generic filler."""


async def _verify_subject(session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID) -> None:
    subject = await SubjectRepository(session).get_by_id_for_user(subject_id, user_id)
    if subject is None:
        raise NotFoundError(f"Subject {subject_id} not found")


# --- flashcards ---


async def generate_flashcards(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID
) -> GenerateFlashcardsResponse:
    """Deterministic, not an LLM call: one flashcard per concept/skill that
    has a definition and doesn't already have one. Cheap, instant, and
    always available as soon as Phase 4 has produced concepts."""
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    repository = LearnRepository(session)
    concepts = await CurriculumRepository(session).list_concepts(subject_id)

    created = 0
    skipped = 0
    for concept in concepts:
        if concept.concept_type not in _FLASHCARD_CONCEPT_TYPES or not concept.definition:
            continue
        if await repository.flashcard_exists_for_concept(concept.id):
            skipped += 1
            continue
        await repository.create_flashcard(
            Flashcard(
                subject_id=subject_id,
                concept_id=concept.id,
                front=f"What is {concept.canonical_name}?",
                back=concept.definition,
                source_grounded=True,
            )
        )
        created += 1

    await session.commit()
    return GenerateFlashcardsResponse(created=created, skipped_existing=skipped)


async def create_flashcard(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID, data: FlashcardCreate
) -> Flashcard:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    concept = await CurriculumRepository(session).get_concept(subject_id, data.concept_id)
    if concept is None:
        raise NotFoundError(f"Concept {data.concept_id} not found")
    flashcard = await LearnRepository(session).create_flashcard(
        Flashcard(
            subject_id=subject_id,
            concept_id=data.concept_id,
            front=data.front,
            back=data.back,
            source_grounded=False,
        )
    )
    await session.commit()
    return flashcard


async def list_flashcards(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID
) -> list[Flashcard]:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    return await LearnRepository(session).list_flashcards(subject_id)


async def update_flashcard(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    subject_id: uuid.UUID,
    flashcard_id: uuid.UUID,
    data: FlashcardUpdate,
) -> Flashcard:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    repository = LearnRepository(session)
    flashcard = await repository.get_flashcard(subject_id, flashcard_id)
    if flashcard is None:
        raise NotFoundError(f"Flashcard {flashcard_id} not found")
    if data.front is not None:
        flashcard.front = data.front
    if data.back is not None:
        flashcard.back = data.back
    await session.commit()
    return flashcard


async def delete_flashcard(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID, flashcard_id: uuid.UUID
) -> None:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    repository = LearnRepository(session)
    flashcard = await repository.get_flashcard(subject_id, flashcard_id)
    if flashcard is None:
        raise NotFoundError(f"Flashcard {flashcard_id} not found")
    await repository.delete_flashcard(flashcard)
    await session.commit()


# --- study guide ---


def _format_concepts_for_guide(concepts: list[Concept], edges: list[ConceptEdge]) -> str:
    concept_by_id = {c.id: c for c in concepts}
    lines = [f"- [{c.concept_type}] {c.canonical_name}: {c.definition or '(no definition yet)'}" for c in concepts]
    edge_lines = []
    for edge in edges:
        source = concept_by_id.get(edge.source_concept_id)
        target = concept_by_id.get(edge.target_concept_id)
        if source and target:
            edge_lines.append(f"- {source.canonical_name} {edge.relation} {target.canonical_name}")
    return "Concepts:\n" + "\n".join(lines) + "\n\nRelationships:\n" + "\n".join(edge_lines)


async def generate_study_guide(
    session: AsyncSession,
    generation_provider: GenerationProvider,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    subject_id: uuid.UUID,
) -> StudyGuide:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    curriculum_repository = CurriculumRepository(session)
    concepts = await curriculum_repository.list_concepts(subject_id)
    concepts = [c for c in concepts if c.status != "REJECTED"]
    if not concepts:
        raise ValidationFailedError(
            "No concepts to build a study guide from yet. Run \"Build curriculum\" for this "
            "subject first."
        )
    edges = await curriculum_repository.list_edges_for_subject(subject_id)

    user_turn = _format_concepts_for_guide(concepts, edges)
    content = await generation_provider.generate(
        system_instruction=_STUDY_GUIDE_SYSTEM_INSTRUCTION,
        user_message=user_turn,
        model=settings.reasoning_model,
    )

    guide = await LearnRepository(session).upsert_study_guide(subject_id, content)
    await session.commit()
    return guide


async def get_study_guide(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID
) -> StudyGuide | None:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    return await LearnRepository(session).get_study_guide(subject_id)
