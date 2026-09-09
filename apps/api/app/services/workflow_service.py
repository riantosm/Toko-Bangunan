from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.models.workflow import StepType, WorkflowStep
from app.schemas.workflow import WorkflowStepRead

VALID_OUTCOMES = {"approved", "rejected", "skipped"}


def _now() -> datetime:
    return datetime.now(UTC)


def step_to_read(step: WorkflowStep) -> WorkflowStepRead:
    return WorkflowStepRead(
        id=step.id,
        order_id=step.order_id,
        seq=step.seq,
        step_type_name=step.step_type.name,
        assigned_at=step.assigned_at,
        completed_at=step.completed_at,
        outcome=step.outcome,
        sla_target_minutes=step.sla_target_minutes,
        elapsed_minutes=(float(step.elapsed_minutes) if step.elapsed_minutes is not None else None),
    )


async def confirm_order(session: AsyncSession, order_id: int) -> Order:
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order tidak ditemukan")
    if order.status != "draft":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"order berstatus '{order.status}', tidak bisa dikonfirmasi",
        )

    step_types = (await session.scalars(select(StepType).order_by(StepType.seq))).all()
    if not step_types:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "step_types belum di-seed")

    for i, st in enumerate(step_types):
        session.add(
            WorkflowStep(
                order_id=order.id,
                step_type_id=st.id,
                seq=st.seq,
                sla_target_minutes=st.default_sla_minutes,
                assigned_at=_now() if i == 0 else None,
            )
        )
    order.status = "confirmed"
    await session.commit()
    return order


async def list_steps(session: AsyncSession, order_id: int) -> list[WorkflowStep]:
    return list(
        await session.scalars(
            select(WorkflowStep)
            .where(WorkflowStep.order_id == order_id)
            .options(selectinload(WorkflowStep.step_type))
            .order_by(WorkflowStep.seq)
        )
    )


async def complete_step(session: AsyncSession, step_id: int, outcome: str) -> WorkflowStep:
    if outcome not in VALID_OUTCOMES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"outcome harus salah satu dari {sorted(VALID_OUTCOMES)}",
        )

    step = await session.get(WorkflowStep, step_id)
    if step is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "langkah tidak ditemukan")
    if step.assigned_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "langkah ini belum aktif")
    if step.completed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "langkah ini sudah selesai")

    step.completed_at = _now()
    step.outcome = outcome
    await session.flush()

    order = await session.get(Order, step.order_id)
    assert order is not None

    if outcome == "rejected":
        order.status = "rejected"
    else:
        next_step = await session.scalar(
            select(WorkflowStep)
            .where(
                WorkflowStep.order_id == step.order_id,
                WorkflowStep.seq > step.seq,
            )
            .order_by(WorkflowStep.seq)
            .limit(1)
        )
        if next_step is not None:
            next_step.assigned_at = _now()
        else:
            order.status = "done"
            order.completed_at = _now()

    await session.commit()
    await session.refresh(step)

    fresh = await session.scalar(
        select(WorkflowStep)
        .where(WorkflowStep.id == step_id)
        .options(selectinload(WorkflowStep.step_type))
    )
    assert fresh is not None
    return fresh
