from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db_session
from app.core.exceptions import ConflictError
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.user import UserCreate, UserRead

router = APIRouter(tags=["users"])


@router.post("/users", response_model=UserRead, status_code=201)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db_session),
) -> User:
    existing = await user_crud.get_by_email(db, email=user_in.email)
    if existing is not None:
        raise ConflictError("A user with this email already exists")
    return await user_crud.create_user(db, obj_in=user_in)


@router.get("/users/me", response_model=UserRead)
async def read_current_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    return current_user
