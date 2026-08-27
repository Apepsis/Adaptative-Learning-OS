from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.modules.identity.models import User
from app.modules.identity.schemas import UserRead

router = APIRouter(prefix="/v1/me", tags=["identity"])


@router.get("", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
