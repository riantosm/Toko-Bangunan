import asyncio
import sys

from app.core.db import SessionLocal
from app.services.conversation_service import handle_incoming


async def main() -> None:
    wa_id = "628123456789"
    msg = sys.argv[1] if len(sys.argv) > 1 else "pak mau 3 sak semen tiga roda"
    async with SessionLocal() as s:
        reply = await handle_incoming(s, wa_id=wa_id, body=msg, name_hint="Pak Budi")
        await s.commit()
    print("--- REPLY ---")
    print(reply)


if __name__ == "__main__":
    asyncio.run(main())
