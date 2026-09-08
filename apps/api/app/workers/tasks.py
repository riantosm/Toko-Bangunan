import asyncio
from typing import Any

from app.core.db import SessionLocal
from app.services.order_service import run_intake


async def ping(ctx: dict[str, Any], name: str) -> str:
    await asyncio.sleep(1)
    print(f"[worker] ping dari {name}")
    return f"pong: {name}"


async def process_intake_job(
    ctx: dict[str, Any], job_id: str, customer_name: str, body: str
) -> None:
    async with SessionLocal() as session:
        await run_intake(session, job_id, customer_name, body)
