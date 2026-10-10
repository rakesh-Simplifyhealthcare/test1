from collections.abc import AsyncGenerator

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.crud.user import user_crud
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if email is None:
            raise UnauthorizedError("Could not validate credentials")
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Could not validate credentials") from exc

    user = await user_crud.get_by_email(db, email=email)
    if user is None:
        raise UnauthorizedError("Could not validate credentials")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise UnauthorizedError("Inactive user")
    return current_user
