import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.embeddings.factory import get_embedding_provider
from app.ai.providers.base import GenerationProvider
from app.ai.providers.factory import get_generation_provider
from app.core.config import Settings, get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.notebooks import service
from app.modules.notebooks.schemas import (
    AddSourceRequest,
    ChatMessageListResponse,
    ChatMessageRead,
    ChatRequest,
    NotebookCreate,
    NotebookListResponse,
    NotebookRead,
    NotebookSourceListResponse,
    NotebookSourceRead,
    NoteCreate,
    NoteListResponse,
    NoteRead,
    NoteUpdate,
)

router = APIRouter(prefix="/v1/notebooks", tags=["notebooks"])

# Domain errors (NotFoundError, ConflictError, AIProviderError) are mapped
# to HTTP responses by the global handlers in app.main.


@router.post("", response_model=NotebookRead, status_code=status.HTTP_201_CREATED)
async def create_notebook(
    payload: NotebookCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotebookRead:
    notebook = await service.create_notebook(session, user_id=current_user.id, data=payload)
    return NotebookRead.model_validate(notebook)


@router.get("", response_model=NotebookListResponse)
async def list_notebooks(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotebookListResponse:
    notebooks = await service.list_notebooks(session, user_id=current_user.id)
    return NotebookListResponse(
        items=[NotebookRead.model_validate(n) for n in notebooks], total=len(notebooks)
    )


@router.get("/{notebook_id}", response_model=NotebookRead)
async def get_notebook(
    notebook_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotebookRead:
    notebook = await service.get_notebook(session, user_id=current_user.id, notebook_id=notebook_id)
    return NotebookRead.model_validate(notebook)


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(
    notebook_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.delete_notebook(session, user_id=current_user.id, notebook_id=notebook_id)


@router.post("/{notebook_id}/sources", status_code=status.HTTP_204_NO_CONTENT)
async def add_source(
    notebook_id: uuid.UUID,
    payload: AddSourceRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.add_source(
        session, user_id=current_user.id, notebook_id=notebook_id, source_id=payload.source_id
    )


@router.delete("/{notebook_id}/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_source(
    notebook_id: uuid.UUID,
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.remove_source(
        session, user_id=current_user.id, notebook_id=notebook_id, source_id=source_id
    )


@router.get("/{notebook_id}/sources", response_model=NotebookSourceListResponse)
async def list_sources(
    notebook_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotebookSourceListResponse:
    pairs = await service.list_sources(session, user_id=current_user.id, notebook_id=notebook_id)
    return NotebookSourceListResponse(
        items=[
            NotebookSourceRead(
                source_id=source.id, title=source.title, status=source.status, added_at=ns.added_at
            )
            for ns, source in pairs
        ]
    )


@router.post("/{notebook_id}/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    notebook_id: uuid.UUID,
    payload: NoteCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteRead:
    note = await service.create_note(
        session, user_id=current_user.id, notebook_id=notebook_id, data=payload
    )
    return NoteRead.model_validate(note)


@router.get("/{notebook_id}/notes", response_model=NoteListResponse)
async def list_notes(
    notebook_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteListResponse:
    notes = await service.list_notes(session, user_id=current_user.id, notebook_id=notebook_id)
    return NoteListResponse(items=[NoteRead.model_validate(n) for n in notes])


@router.patch("/{notebook_id}/notes/{note_id}", response_model=NoteRead)
async def update_note(
    notebook_id: uuid.UUID,
    note_id: uuid.UUID,
    payload: NoteUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteRead:
    note = await service.update_note(
        session, user_id=current_user.id, notebook_id=notebook_id, note_id=note_id, data=payload
    )
    return NoteRead.model_validate(note)


@router.delete("/{notebook_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    notebook_id: uuid.UUID,
    note_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.delete_note(session, user_id=current_user.id, notebook_id=notebook_id, note_id=note_id)


@router.get("/{notebook_id}/messages", response_model=ChatMessageListResponse)
async def list_messages(
    notebook_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessageListResponse:
    messages = await service.list_messages(session, user_id=current_user.id, notebook_id=notebook_id)
    return ChatMessageListResponse(items=[ChatMessageRead.model_validate(m) for m in messages])


@router.post("/{notebook_id}/chat", response_model=ChatMessageRead, status_code=status.HTTP_201_CREATED)
async def chat(
    notebook_id: uuid.UUID,
    payload: ChatRequest,
    session: AsyncSession = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    generation_provider: GenerationProvider = Depends(get_generation_provider),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> ChatMessageRead:
    assistant_message = await service.chat(
        session,
        embedding_provider,
        generation_provider,
        settings,
        user_id=current_user.id,
        notebook_id=notebook_id,
        message=payload.message,
    )
    return ChatMessageRead.model_validate(assistant_message)
