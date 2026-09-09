from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if creds is None:
        raise UnauthorizedError("butuh login")
    try:
        payload = decode_token(creds.credentials)
    except Exception as exc:
        raise UnauthorizedError("token tidak valid / kedaluwarsa") from exc

    user = await session.get(User, int(payload["sub"]))
    if user is None:
        raise UnauthorizedError("user tidak ditemukan")
    return user


def require_role(*roles: str):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError(f"perlu role: {', '.join(roles)}")
        return user

    return checker
