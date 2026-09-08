from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.tasks import ping


class WorkerSettings:
    functions = [ping]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
