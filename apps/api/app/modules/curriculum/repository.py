import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.curriculum.models import Concept, ConceptAlias, ConceptEdge, ConceptEvidence
from app.modules.retrieval.models import Chunk
from app.modules.sources.models import Source

_DEFAULT_CHUNK_SAMPLE_LIMIT = 60


class CurriculumRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- concepts ---

    async def create_concept(self, concept: Concept) -> Concept:
        self._session.add(concept)
        await self._session.flush()
        return concept

    async def get_concept(self, subject_id: uuid.UUID, concept_id: uuid.UUID) -> Concept | None:
        result = await self._session.execute(
            select(Concept).where(Concept.id == concept_id, Concept.subject_id == subject_id)
        )
        return result.scalar_one_or_none()

    async def list_concepts(self, subject_id: uuid.UUID) -> list[Concept]:
        result = await self._session.execute(
            select(Concept).where(Concept.subject_id == subject_id).order_by(Concept.canonical_name)
        )
        return list(result.scalars().all())

    async def find_by_name_or_alias(self, subject_id: uuid.UUID, normalized_name: str) -> Concept | None:
        """Exact normalized-name or alias match (blueprint 11.5's first two
        dedup steps; embedding-similarity fuzzy matching and LLM
        adjudication are deferred — see the curriculum ADR)."""
        result = await self._session.execute(
            select(Concept)
            .outerjoin(ConceptAlias, ConceptAlias.concept_id == Concept.id)
            .where(
                Concept.subject_id == subject_id,
                or_(
                    func.lower(Concept.canonical_name) == normalized_name,
                    func.lower(ConceptAlias.alias) == normalized_name,
                ),
            )
            .limit(1)
        )
        return result.scalars().first()

    async def delete_concept(self, concept: Concept) -> None:
        await self._session.delete(concept)

    async def update_concept(self, concept: Concept, **fields: object) -> Concept:
        for key, value in fields.items():
            if value is not None:
                setattr(concept, key, value)
        await self._session.flush()
        return concept

    async def slug_exists(self, subject_id: uuid.UUID, slug: str) -> bool:
        result = await self._session.execute(
            select(func.count()).select_from(Concept).where(Concept.subject_id == subject_id, Concept.slug == slug)
        )
        return (result.scalar_one() or 0) > 0

    # --- aliases ---

    async def add_alias(self, concept_id: uuid.UUID, alias: str) -> None:
        exists = await self._session.execute(
            select(func.count())
            .select_from(ConceptAlias)
            .where(ConceptAlias.concept_id == concept_id, func.lower(ConceptAlias.alias) == alias.lower())
        )
        if (exists.scalar_one() or 0) == 0:
            self._session.add(ConceptAlias(concept_id=concept_id, alias=alias))
            await self._session.flush()

    # --- edges ---

    async def create_edge(self, edge: ConceptEdge) -> ConceptEdge:
        self._session.add(edge)
        await self._session.flush()
        return edge

    async def edge_exists(
        self, source_concept_id: uuid.UUID, target_concept_id: uuid.UUID, relation: str
    ) -> bool:
        result = await self._session.execute(
            select(func.count())
            .select_from(ConceptEdge)
            .where(
                ConceptEdge.source_concept_id == source_concept_id,
                ConceptEdge.target_concept_id == target_concept_id,
                ConceptEdge.relation == relation,
            )
        )
        return (result.scalar_one() or 0) > 0

    async def list_edges_for_subject(self, subject_id: uuid.UUID) -> list[ConceptEdge]:
        result = await self._session.execute(select(ConceptEdge).where(ConceptEdge.subject_id == subject_id))
        return list(result.scalars().all())

    async def list_edges_for_concept(self, concept_id: uuid.UUID) -> tuple[list[ConceptEdge], list[ConceptEdge]]:
        outgoing = await self._session.execute(
            select(ConceptEdge).where(ConceptEdge.source_concept_id == concept_id)
        )
        incoming = await self._session.execute(
            select(ConceptEdge).where(ConceptEdge.target_concept_id == concept_id)
        )
        return list(outgoing.scalars().all()), list(incoming.scalars().all())

    async def reassign_edges(self, from_concept_id: uuid.UUID, to_concept_id: uuid.UUID) -> None:
        """Used by merge: point every edge touching `from_concept_id` at
        `to_concept_id` instead. Edges that would become self-loops or
        duplicates of an existing edge are dropped rather than reassigned."""
        outgoing, incoming = await self.list_edges_for_concept(from_concept_id)
        for edge in outgoing:
            if edge.target_concept_id == to_concept_id or await self.edge_exists(
                to_concept_id, edge.target_concept_id, edge.relation
            ):
                await self._session.delete(edge)
            else:
                edge.source_concept_id = to_concept_id
        for edge in incoming:
            if edge.source_concept_id == to_concept_id or await self.edge_exists(
                edge.source_concept_id, to_concept_id, edge.relation
            ):
                await self._session.delete(edge)
            else:
                edge.target_concept_id = to_concept_id
        await self._session.flush()

    # --- evidence ---

    async def add_evidence(self, concept_id: uuid.UUID, chunk_id: uuid.UUID) -> None:
        exists = await self._session.execute(
            select(func.count())
            .select_from(ConceptEvidence)
            .where(ConceptEvidence.concept_id == concept_id, ConceptEvidence.chunk_id == chunk_id)
        )
        if (exists.scalar_one() or 0) == 0:
            self._session.add(ConceptEvidence(concept_id=concept_id, chunk_id=chunk_id))
            await self._session.flush()

    async def list_evidence_chunk_ids(self, concept_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(ConceptEvidence.chunk_id).where(ConceptEvidence.concept_id == concept_id)
        )
        return list(result.scalars().all())

    async def reassign_evidence(self, from_concept_id: uuid.UUID, to_concept_id: uuid.UUID) -> None:
        """Row-by-row (not a single UPDATE) because concept_evidence has a
        unique (concept_id, chunk_id) constraint — a blind bulk UPDATE would
        raise an IntegrityError whenever both concepts already cite the
        same chunk, instead of just dropping the now-duplicate row."""
        existing_target_chunks = set(await self.list_evidence_chunk_ids(to_concept_id))
        result = await self._session.execute(
            select(ConceptEvidence).where(ConceptEvidence.concept_id == from_concept_id)
        )
        for row in result.scalars().all():
            if row.chunk_id in existing_target_chunks:
                await self._session.delete(row)
            else:
                row.concept_id = to_concept_id
                existing_target_chunks.add(row.chunk_id)
        await self._session.flush()

    # --- chunk sampling for extraction ---

    async def sample_chunks_for_subject(
        self, subject_id: uuid.UUID, user_id: uuid.UUID, limit: int = _DEFAULT_CHUNK_SAMPLE_LIMIT
    ) -> list[Chunk]:
        result = await self._session.execute(
            select(Chunk)
            .join(Source, Source.id == Chunk.source_id)
            .where(Chunk.subject_id == subject_id, Source.user_id == user_id)
            .order_by(Source.source_role.is_(None), Chunk.source_id, Chunk.page_start)
            .limit(limit)
        )
        return list(result.scalars().all())
