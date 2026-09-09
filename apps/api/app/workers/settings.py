from typing import ClassVar

from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.tasks import ping, process_intake_job


class WorkerSettings:
    functions: ClassVar = [ping, process_intake_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
