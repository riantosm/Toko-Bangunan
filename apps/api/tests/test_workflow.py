import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.models.order import Order
from app.models.workflow import StepType
from app.services import workflow_service


@pytest_asyncio.fixture
async def step_types(session) -> list[StepType]:
    rows = [
        StepType(name="Verifikasi Stok", seq=1, default_sla_minutes=60),
        StepType(name="Approval Manajer", seq=2, default_sla_minutes=240),
        StepType(name="Konfirmasi Pembayaran", seq=3, default_sla_minutes=120),
    ]
    session.add_all(rows)
    await session.commit()
    return rows


@pytest_asyncio.fixture
async def order(session) -> Order:
    o = Order(customer_name="Andi", status="draft")
    session.add(o)
    await session.commit()
    return o


async def test_confirm_creates_three_steps(session, step_types, order) -> None:
    await workflow_service.confirm_order(session, order.id)
    await session.refresh(order)

    assert order.status == "confirmed"
    steps = await workflow_service.list_steps(session, order.id)
    assert [s.seq for s in steps] == [1, 2, 3]
    assert steps[0].assigned_at is not None
    assert steps[1].assigned_at is None


async def test_confirm_twice_conflicts(session, step_types, order) -> None:
    await workflow_service.confirm_order(session, order.id)
    with pytest.raises(HTTPException) as exc:
        await workflow_service.confirm_order(session, order.id)
    assert exc.value.status_code == 409


async def test_complete_step_activates_next(session, step_types, order) -> None:
    await workflow_service.confirm_order(session, order.id)
    steps = await workflow_service.list_steps(session, order.id)

    await workflow_service.complete_step(session, steps[0].id, "approved")

    steps = await workflow_service.list_steps(session, order.id)
    assert steps[0].completed_at is not None
    assert steps[0].elapsed_minutes is not None
    assert steps[1].assigned_at is not None


async def test_complete_last_step_marks_order_done(session, step_types, order) -> None:
    await workflow_service.confirm_order(session, order.id)
    steps = await workflow_service.list_steps(session, order.id)
    for st in steps:
        await workflow_service.complete_step(session, st.id, "approved")

    await session.refresh(order)
    assert order.status == "done"
    assert order.completed_at is not None


async def test_reject_marks_order_rejected(session, step_types, order) -> None:
    await workflow_service.confirm_order(session, order.id)
    steps = await workflow_service.list_steps(session, order.id)

    await workflow_service.complete_step(session, steps[0].id, "rejected")

    await session.refresh(order)
    assert order.status == "rejected"


async def test_cannot_complete_inactive_step(session, step_types, order) -> None:
    await workflow_service.confirm_order(session, order.id)
    steps = await workflow_service.list_steps(session, order.id)

    with pytest.raises(HTTPException) as exc:
        await workflow_service.complete_step(session, steps[1].id, "approved")
    assert exc.value.status_code == 409
