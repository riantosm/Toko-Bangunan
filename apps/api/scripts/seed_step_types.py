import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.workflow import StepType

STEPS = [
    ("Verifikasi Stok", 1, 60),
    ("Approval Manajer", 2, 240),
    ("Konfirmasi Pembayaran", 3, 120),
]


async def main() -> None:
    async with SessionLocal() as session:
        for name, seq, sla in STEPS:
            if await session.scalar(select(StepType).where(StepType.name == name)):
                continue
            session.add(StepType(name=name, seq=seq, default_sla_minutes=sla))
        await session.commit()
    print("seed step_types selesai")


if __name__ == "__main__":
    asyncio.run(main())
