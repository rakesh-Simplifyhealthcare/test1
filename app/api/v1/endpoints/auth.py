from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.crud.user import user_crud
from app.schemas.user import Token

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
) -> Token:
    user = await user_crud.get_by_email(db, email=form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")

    access_token = create_access_token(subject=user.email)
    return Token(access_token=access_token)
