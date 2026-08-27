import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.subjects.models import Subject
from app.modules.subjects.repository import SubjectRepository
from app.modules.subjects.schemas import SubjectCreate

_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = _SLUG_STRIP_RE.sub("-", value.strip().lower()).strip("-")
    return slug or "subject"


async def create_subject(session: AsyncSession, *, user_id: uuid.UUID, data: SubjectCreate) -> Subject:
    repository = SubjectRepository(session)
    base_slug = slugify(data.name)
    slug = base_slug
    suffix = 2
    while await repository.slug_exists_for_user(slug, user_id):
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    subject = Subject(
        user_id=user_id,
        name=data.name,
        slug=slug,
        description=data.description,
        subject_type=data.subject_type,
        color_token=data.color_token,
    )
    subject = await repository.create(subject)
    await session.commit()
    return subject


async def list_subjects(session: AsyncSession, *, user_id: uuid.UUID) -> list[Subject]:
    return await SubjectRepository(session).list_for_user(user_id)


async def get_subject(session: AsyncSession, *, user_id: uuid.UUID, subject_id: uuid.UUID) -> Subject:
    subject = await SubjectRepository(session).get_by_id_for_user(subject_id, user_id)
    if subject is None:
        raise NotFoundError(f"Subject {subject_id} not found")
    return subject
