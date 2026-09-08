from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from app.core.config import settings

_pool: ArqRedis | None = None


async def get_queue() -> ArqRedis:
    """Pool Redis untuk meng-enqueue job dari FastAPI (dibuat sekali, dipakai ulang)."""
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool
