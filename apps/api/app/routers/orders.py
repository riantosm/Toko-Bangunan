from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.schemas.order import (
    OrderCreate,
    OrderIntakeRequest,
    OrderIntakeResponse,
    OrderListResponse,
    OrderRead,
)
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate, session: AsyncSession = Depends(get_session)
) -> OrderRead:
    order = await order_service.create_order(session, payload)
    return OrderRead.model_validate(order)


@router.post(
    "/intake",
    response_model=OrderIntakeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def intake_order(
    payload: OrderIntakeRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> OrderIntakeResponse:
    job = await order_service.enqueue_intake(
        session, payload.customer_name, payload.body
    )
    response.headers["Location"] = f"/jobs/{job.id}"
    return OrderIntakeResponse(job_id=job.id)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> OrderListResponse:
    return await order_service.list_orders(session, page, size)


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int, session: AsyncSession = Depends(get_session)
) -> OrderRead:
    order = await order_service.get_order(session, order_id)
    return OrderRead.model_validate(order)
