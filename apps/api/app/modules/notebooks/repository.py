import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notebooks.models import Notebook, NotebookMessage, NotebookNote, NotebookSource
from app.modules.sources.models import Source


class NotebookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, notebook: Notebook) -> Notebook:
        self._session.add(notebook)
        await self._session.flush()
        return notebook

    async def get_by_id_for_user(self, notebook_id: uuid.UUID, user_id: uuid.UUID) -> Notebook | None:
        result = await self._session.execute(
            select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[Notebook]:
        result = await self._session.execute(
            select(Notebook).where(Notebook.user_id == user_id).order_by(Notebook.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, notebook: Notebook) -> None:
        await self._session.delete(notebook)

    async def add_source(self, notebook_id: uuid.UUID, source_id: uuid.UUID) -> None:
        self._session.add(NotebookSource(notebook_id=notebook_id, source_id=source_id))
        await self._session.flush()

    async def remove_source(self, notebook_id: uuid.UUID, source_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(NotebookSource).where(
                NotebookSource.notebook_id == notebook_id, NotebookSource.source_id == source_id
            )
        )

    async def is_source_linked(self, notebook_id: uuid.UUID, source_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(NotebookSource.id).where(
                NotebookSource.notebook_id == notebook_id, NotebookSource.source_id == source_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def list_sources(self, notebook_id: uuid.UUID) -> list[tuple[NotebookSource, Source]]:
        result = await self._session.execute(
            select(NotebookSource, Source)
            .join(Source, Source.id == NotebookSource.source_id)
            .where(NotebookSource.notebook_id == notebook_id)
            .order_by(NotebookSource.added_at.desc())
        )
        return [(ns, source) for ns, source in result.all()]

    async def active_source_ids(self, notebook_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(NotebookSource.source_id).where(NotebookSource.notebook_id == notebook_id)
        )
        return list(result.scalars().all())

    async def create_note(self, note: NotebookNote) -> NotebookNote:
        self._session.add(note)
        await self._session.flush()
        return note

    async def get_note(self, notebook_id: uuid.UUID, note_id: uuid.UUID) -> NotebookNote | None:
        result = await self._session.execute(
            select(NotebookNote).where(
                NotebookNote.id == note_id, NotebookNote.notebook_id == notebook_id
            )
        )
        return result.scalar_one_or_none()

    async def list_notes(self, notebook_id: uuid.UUID) -> list[NotebookNote]:
        result = await self._session.execute(
            select(NotebookNote)
            .where(NotebookNote.notebook_id == notebook_id)
            .order_by(NotebookNote.updated_at.desc())
        )
        return list(result.scalars().all())

    async def delete_note(self, note: NotebookNote) -> None:
        await self._session.delete(note)

    async def add_message(self, message: NotebookMessage) -> NotebookMessage:
        self._session.add(message)
        await self._session.flush()
        return message

    async def list_messages(self, notebook_id: uuid.UUID) -> list[NotebookMessage]:
        result = await self._session.execute(
            select(NotebookMessage)
            .where(NotebookMessage.notebook_id == notebook_id)
            .order_by(NotebookMessage.created_at.asc())
        )
        return list(result.scalars().all())
