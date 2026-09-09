from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.errors import RateLimitError
from app.models.user import User

WINDOW_SECONDS = 60

_SQL = text(
    """
    INSERT INTO rate_counters (bucket_key, window_start, count)
    VALUES (:k, :w, 1)
    ON CONFLICT (bucket_key, window_start)
    DO UPDATE SET count = rate_counters.count + 1
    RETURNING count
    """
)


def rate_limit(*, scope: str, limit_setting: str) -> Callable[..., Coroutine[Any, Any, None]]:
    async def dep(
        response: Response,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> None:
        limit = int(getattr(settings, limit_setting))
        now = datetime.now(UTC)
        window_start = now.replace(second=0, microsecond=0)
        bucket_key = f"{scope}:user:{user.id}"

        count = await session.scalar(_SQL, {"k": bucket_key, "w": window_start})
        await session.commit()
        count = int(count or 0)

        reset_epoch = int(window_start.timestamp()) + WINDOW_SECONDS
        rl_headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, limit - count)),
            "X-RateLimit-Reset": str(reset_epoch),
        }
        for key, value in rl_headers.items():
            response.headers[key] = value

        if count > limit:
            retry_after = max(1, reset_epoch - int(now.timestamp()))
            raise RateLimitError(
                f"terlalu banyak permintaan, coba lagi dalam {retry_after} detik",
                details={"retry_after": retry_after},
                headers={**rl_headers, "Retry-After": str(retry_after)},
            )

    return dep
