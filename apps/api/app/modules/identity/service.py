from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.identity.repository import UserRepository


async def get_or_create_local_user(session: AsyncSession, email: str) -> User:
    """Resolve the single local user for LOCAL_SINGLE_USER mode.

    Real multi-user auth (OAuth/JWT, section 27 of the blueprint) lands in a
    later phase; this is the documented MVP shortcut, not a permanent design.
    """
    repository = UserRepository(session)
    user = await repository.get_by_email(email)
    if user is not None:
        return user
    user = await repository.create(email=email)
    await session.commit()
    return user
