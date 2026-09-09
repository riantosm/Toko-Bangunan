import asyncio
from typing import Any

from app.core.db import SessionLocal
from app.services.conversation_service import handle_incoming
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


async def process_wa_message(
    ctx: dict[str, Any], wa_id: str, body: str, name_hint: str = ""
) -> None:
    async with SessionLocal() as session:
        await handle_incoming(session, wa_id=wa_id, body=body, name_hint=name_hint)
        await session.commit()
