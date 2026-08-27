import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import GenerationProvider
from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.modules.curriculum.graph import would_create_cycle
from app.modules.curriculum.models import Concept, ConceptEdge, ConceptProvenance, ConceptStatus
from app.modules.curriculum.repository import CurriculumRepository
from app.modules.curriculum.schemas import (
    BuildCurriculumResponse,
    ConceptExtractionResult,
    ConceptUpdate,
)
from app.modules.subjects.repository import SubjectRepository

# Extraction is grounded strictly in the user's own uploaded material — no
# outside knowledge is asked for, matching the source-first principle
# (blueprint section 3.3): every concept must trace back to evidence.
_EXTRACTION_SYSTEM_INSTRUCTION = """You are analyzing a student's own uploaded academic material to \
extract the key concepts it teaches, for a personal knowledge map.

You will be given numbered evidence excerpts from the student's own sources. Extract concepts \
strictly from this evidence — do not invent concepts the material doesn't actually cover, and do \
not use outside knowledge to embellish a definition beyond what the evidence supports.

For each concept:
- Give it a clear, canonical name (e.g. "Projectile motion", not "PM" or an overly generic term).
- Write a one-to-two sentence definition, grounded in the evidence.
- Classify concept_type as one of: "topic" (a broad unit, e.g. "Kinematics"), "subtopic" (e.g. \
"Projectile motion"), "concept" (a specific idea within a subtopic, e.g. "Time of flight"), or \
"skill" (a procedure, e.g. "Decomposing initial velocity into components").
- List which evidence numbers support it in evidence_indices.
- Add aliases where the material uses alternate names or abbreviations.
- Add edges to OTHER concepts you are extracting in this same batch, referencing their exact \
name. Use PART_OF for a subtopic/concept under a topic, PREREQUISITE_OF when understanding one is \
required before the other, and the remaining relation types only where the evidence clearly \
supports them. Only add an edge the evidence actually supports.

It is fine to extract a flat list with few or no edges if the material doesn't support a rigid \
hierarchy — do not fabricate structure that isn't there."""

_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def normalize_concept_name(name: str) -> str:
    return name.strip().lower()


def _slugify(name: str) -> str:
    slug = _SLUG_STRIP_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "concept"


async def _unique_slug(repository: CurriculumRepository, subject_id: uuid.UUID, name: str) -> str:
    base = _slugify(name)
    slug = base
    suffix = 2
    while await repository.slug_exists(subject_id, slug):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def _format_indexed_evidence(chunks: list) -> str:
    return "\n".join(f"[{index}] {chunk.text}" for index, chunk in enumerate(chunks))


async def _verify_subject(session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID) -> None:
    subject = await SubjectRepository(session).get_by_id_for_user(subject_id, user_id)
    if subject is None:
        raise NotFoundError(f"Subject {subject_id} not found")


async def build_curriculum(
    session: AsyncSession,
    generation_provider: GenerationProvider,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    subject_id: uuid.UUID,
) -> BuildCurriculumResponse:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    repository = CurriculumRepository(session)

    chunks = await repository.sample_chunks_for_subject(subject_id, user_id)
    if not chunks:
        raise ValidationFailedError(
            "No processed content found for this subject yet. Upload sources, assign them to this "
            "subject, and wait for them to finish processing first."
        )

    user_turn = f"Evidence:\n{_format_indexed_evidence(chunks)}\n\nExtract the key concepts."
    extraction: ConceptExtractionResult = await generation_provider.generate_structured(
        system_instruction=_EXTRACTION_SYSTEM_INSTRUCTION,
        user_message=user_turn,
        model=settings.reasoning_model,
        response_schema=ConceptExtractionResult,
    )

    name_to_id: dict[str, uuid.UUID] = {}
    concepts_created = 0
    concepts_updated = 0

    for extracted in extraction.concepts:
        normalized = normalize_concept_name(extracted.name)
        concept = await repository.find_by_name_or_alias(subject_id, normalized)
        if concept is not None:
            if not concept.definition and extracted.definition:
                await repository.update_concept(concept, definition=extracted.definition)
            concepts_updated += 1
        else:
            slug = await _unique_slug(repository, subject_id, extracted.name)
            concept = await repository.create_concept(
                Concept(
                    subject_id=subject_id,
                    canonical_name=extracted.name,
                    slug=slug,
                    definition=extracted.definition,
                    concept_type=extracted.concept_type,
                    status=ConceptStatus.PROPOSED.value,
                )
            )
            concepts_created += 1

        name_to_id[normalized] = concept.id
        for alias in extracted.aliases:
            await repository.add_alias(concept.id, alias)
        for index in extracted.evidence_indices:
            if 0 <= index < len(chunks):
                await repository.add_evidence(concept.id, chunks[index].id)

    existing_edges = await repository.list_edges_for_subject(subject_id)
    edge_pairs = [(edge.source_concept_id, edge.target_concept_id) for edge in existing_edges]

    edges_created = 0
    edges_skipped_cycle = 0
    for extracted in extraction.concepts:
        source_concept_id = name_to_id.get(normalize_concept_name(extracted.name))
        if source_concept_id is None:
            continue
        for extracted_edge in extracted.edges:
            target_concept_id = name_to_id.get(normalize_concept_name(extracted_edge.target_concept_name))
            if target_concept_id is None or target_concept_id == source_concept_id:
                continue
            if await repository.edge_exists(source_concept_id, target_concept_id, extracted_edge.relation):
                continue
            if would_create_cycle(edge_pairs, source_concept_id, target_concept_id):
                edges_skipped_cycle += 1
                continue
            await repository.create_edge(
                ConceptEdge(
                    subject_id=subject_id,
                    source_concept_id=source_concept_id,
                    target_concept_id=target_concept_id,
                    relation=extracted_edge.relation,
                    provenance_type=ConceptProvenance.MODEL.value,
                    approved=True,
                )
            )
            edge_pairs.append((source_concept_id, target_concept_id))
            edges_created += 1

    await session.commit()
    return BuildCurriculumResponse(
        concepts_created=concepts_created,
        concepts_updated=concepts_updated,
        edges_created=edges_created,
        edges_skipped_cycle=edges_skipped_cycle,
        chunks_considered=len(chunks),
    )


async def list_concepts(session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID) -> list[Concept]:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    return await CurriculumRepository(session).list_concepts(subject_id)


async def get_concept(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID, concept_id: uuid.UUID
) -> tuple[Concept, list[ConceptEdge], list[ConceptEdge], list[uuid.UUID]]:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    repository = CurriculumRepository(session)
    concept = await repository.get_concept(subject_id, concept_id)
    if concept is None:
        raise NotFoundError(f"Concept {concept_id} not found")
    outgoing, incoming = await repository.list_edges_for_concept(concept_id)
    evidence_chunk_ids = await repository.list_evidence_chunk_ids(concept_id)
    return concept, outgoing, incoming, evidence_chunk_ids


async def update_concept(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    subject_id: uuid.UUID,
    concept_id: uuid.UUID,
    data: ConceptUpdate,
) -> Concept:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    repository = CurriculumRepository(session)
    concept = await repository.get_concept(subject_id, concept_id)
    if concept is None:
        raise NotFoundError(f"Concept {concept_id} not found")

    await repository.update_concept(
        concept,
        canonical_name=data.canonical_name,
        definition=data.definition,
        concept_type=data.concept_type,
        status=data.status,
    )
    await session.commit()
    return concept


async def delete_concept(
    session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID, concept_id: uuid.UUID
) -> None:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    repository = CurriculumRepository(session)
    concept = await repository.get_concept(subject_id, concept_id)
    if concept is None:
        raise NotFoundError(f"Concept {concept_id} not found")
    await repository.delete_concept(concept)
    await session.commit()


async def merge_concepts(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    subject_id: uuid.UUID,
    primary_concept_id: uuid.UUID,
    absorb_concept_id: uuid.UUID,
) -> Concept:
    await _verify_subject(session, user_id=user_id, subject_id=subject_id)
    if primary_concept_id == absorb_concept_id:
        raise ConflictError("Cannot merge a concept into itself")

    repository = CurriculumRepository(session)
    primary = await repository.get_concept(subject_id, primary_concept_id)
    absorb = await repository.get_concept(subject_id, absorb_concept_id)
    if primary is None:
        raise NotFoundError(f"Concept {primary_concept_id} not found")
    if absorb is None:
        raise NotFoundError(f"Concept {absorb_concept_id} not found")

    await repository.reassign_edges(absorb.id, primary.id)
    await repository.reassign_evidence(absorb.id, primary.id)
    await repository.add_alias(primary.id, absorb.canonical_name)
    await repository.delete_concept(absorb)
    await session.commit()
    return primary
