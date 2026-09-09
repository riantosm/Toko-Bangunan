from datetime import UTC, datetime, timedelta

import pytest_asyncio

from app.models.department import Department
from app.models.order import Order
from app.models.workflow import StepType, WorkflowStep
from app.services import metrics_service

NOW = datetime.now(UTC)


@pytest_asyncio.fixture
async def data(session) -> None:
    st = StepType(name="Verifikasi Stok", seq=1, default_sla_minutes=60)
    session.add(st)
    await session.flush()

    def step(order_id: int, assigned_ago_min: float, dur_min: float | None):
        assigned = NOW - timedelta(minutes=assigned_ago_min)
        return WorkflowStep(
            order_id=order_id,
            step_type_id=st.id,
            seq=1,
            sla_target_minutes=60,
            assigned_at=assigned,
            completed_at=(assigned + timedelta(minutes=dur_min)) if dur_min else None,
            outcome="approved" if dur_min else None,
        )

    o1 = Order(customer_name="A", status="done", created_at=NOW - timedelta(days=1))
    o2 = Order(customer_name="B", status="done", created_at=NOW - timedelta(days=2))
    o3 = Order(customer_name="C", status="confirmed", created_at=NOW - timedelta(hours=5))
    session.add_all([o1, o2, o3])
    await session.flush()

    session.add_all(
        [
            step(o1.id, 1500, 30),  # dalam SLA
            step(o2.id, 3000, 120),  # lewat SLA
            step(o3.id, 300, None),  # masih menunggu
        ]
    )
    await session.commit()


async def test_summary(session, data) -> None:
    s = await metrics_service.summary(session, days=30)
    assert s["orders_total"] == 3
    assert s["orders_done"] == 2
    assert s["wip"] == 1
    assert s["sla_met_pct"] == 50.0


async def test_step_durations(session, data) -> None:
    rows = await metrics_service.step_durations(session, days=30)
    assert len(rows) == 1
    assert rows[0]["step_type"] == "Verifikasi Stok"
    assert rows[0]["n"] == 2
    assert rows[0]["breached"] == 1


async def test_aging(session, data) -> None:
    rows = await metrics_service.aging(session)
    assert len(rows) == 1
    assert rows[0]["customer_name"] == "C"
    assert float(rows[0]["waiting_minutes"]) >= 290


async def test_summary_filters_by_department(session, data) -> None:
    gudang = Department(name="Gudang")
    penjualan = Department(name="Penjualan")
    session.add_all([gudang, penjualan])
    await session.flush()

    orders = list(await session.scalars(select_orders()))
    orders[0].department_id = gudang.id
    orders[1].department_id = penjualan.id
    orders[2].department_id = gudang.id
    await session.commit()

    all_ = await metrics_service.summary(session, days=30)
    gd = await metrics_service.summary(session, days=30, department_id=gudang.id)

    assert all_["orders_total"] == 3
    assert gd["orders_total"] == 2  # o1 + o3
    assert gd["wip"] == 1  # o3


def select_orders():
    from sqlalchemy import select

    return select(Order).order_by(Order.id)
