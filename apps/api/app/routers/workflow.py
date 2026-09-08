from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.schemas.workflow import CompleteStepRequest, WorkflowStepRead
from app.services import workflow_service

router = APIRouter(
    tags=["workflow"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: int, session: AsyncSession = Depends(get_session)
) -> dict[str, object]:
    order = await workflow_service.confirm_order(session, order_id)
    return {"id": order.id, "status": order.status}


@router.get("/orders/{order_id}/steps", response_model=list[WorkflowStepRead])
async def list_steps(
    order_id: int, session: AsyncSession = Depends(get_session)
) -> list[WorkflowStepRead]:
    steps = await workflow_service.list_steps(session, order_id)
    return [workflow_service.step_to_read(s) for s in steps]


@router.post(
    "/workflow-steps/{step_id}/complete", response_model=WorkflowStepRead
)
async def complete_step(
    step_id: int,
    payload: CompleteStepRequest,
    session: AsyncSession = Depends(get_session),
) -> WorkflowStepRead:
    step = await workflow_service.complete_step(session, step_id, payload.outcome)
    return workflow_service.step_to_read(step)
