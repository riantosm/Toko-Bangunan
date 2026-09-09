import asyncio
import random

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.department import Department, WorkflowType
from app.models.order import Order
from app.models.user import User

DEPTS = ["Gudang", "Penjualan", "Keuangan"]
WTYPE = "Persetujuan Order"


async def main() -> None:
    random.seed(7)
    async with SessionLocal() as s:
        for name in DEPTS:
            if not await s.scalar(select(Department).where(Department.name == name)):
                s.add(Department(name=name))
        if not await s.scalar(select(WorkflowType).where(WorkflowType.name == WTYPE)):
            s.add(WorkflowType(name=WTYPE))
        await s.commit()

        depts = list(await s.scalars(select(Department)))
        wtype = await s.scalar(select(WorkflowType).where(WorkflowType.name == WTYPE))

        for order in await s.scalars(select(Order)):
            if order.department_id is None:
                order.department_id = random.choice(depts).id
            order.workflow_type_id = wtype.id

        for user in await s.scalars(select(User)):
            if user.department_id is None:
                user.department_id = random.choice(depts).id

        await s.commit()
    print(f"seed: {len(DEPTS)} departments, 1 workflow_type, backfill done")


if __name__ == "__main__":
    asyncio.run(main())
