from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.identity.service import get_or_create_local_user


async def get_current_user(
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Resolve the authenticated user for this request.

    LOCAL_SINGLE_USER mode (the MVP default, blueprint section 27) resolves a
    single local account by email with no login flow. Multi-user auth
    (OAuth/JWT session validation) is a later phase; failing loudly here
    instead of silently trusting a client-supplied id keeps every
    user-scoped query safe once that phase lands.
    """
    if settings.local_single_user:
        return await get_or_create_local_user(session, settings.local_single_user_email)

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Multi-user authentication is not implemented yet. Set LOCAL_SINGLE_USER=true.",
    )
