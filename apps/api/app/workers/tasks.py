import asyncio
from typing import Any


async def ping(ctx: dict[str, Any], name: str) -> str:
    await asyncio.sleep(1)
    print(f"[worker] ping dari {name}")
    return f"pong: {name}"
