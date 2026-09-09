import asyncio
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.models.order import Order
from app.models.workflow import StepType, WorkflowStep

random.seed(42)
NOW = datetime.now(UTC)


async def main() -> None:
    async with SessionLocal() as s:
        step_types = (await s.scalars(select(StepType).order_by(StepType.seq))).all()
        if len(step_types) < 3:
            print("jalankan seed_step_types dulu")
            return

        await s.execute(delete(Order).where(Order.customer_name.like("DEMO %")))
        await s.commit()

        for i in range(40):
            created = NOW - timedelta(days=random.uniform(0, 14), hours=random.uniform(0, 10))
            order = Order(
                customer_name=f"DEMO Pelanggan {i + 1}",
                status="confirmed",
                created_at=created,
            )
            s.add(order)
            await s.flush()

            cursor = created
            done_upto = random.choice([0, 1, 2, 3, 3, 3])
            for idx, st in enumerate(step_types):
                assigned = cursor if idx <= done_upto else None
                completed = None
                if idx < done_upto:
                    dur = random.uniform(0.2, 1.8) * st.default_sla_minutes
                    completed = assigned + timedelta(minutes=dur)
                    cursor = completed
                s.add(
                    WorkflowStep(
                        order_id=order.id,
                        step_type_id=st.id,
                        seq=st.seq,
                        sla_target_minutes=st.default_sla_minutes,
                        assigned_at=assigned,
                        completed_at=completed,
                        outcome="approved" if completed else None,
                    )
                )
            if done_upto == 3:
                order.status = "done"
                order.completed_at = cursor

        await s.commit()
    print("seed demo selesai: 40 order")


if __name__ == "__main__":
    asyncio.run(main())
