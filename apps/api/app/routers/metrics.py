from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_role
from app.services import metrics_service

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    dependencies=[Depends(require_role("manager", "admin"))],
)

Days = Query(30, ge=1, le=365)
Dept = Query(None, alias="department_id")


@router.get("/summary")
async def summary(
    days: int = Days,
    department_id: int | None = Dept,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await metrics_service.summary(session, days, department_id)


@router.get("/step-durations")
async def step_durations(
    days: int = Days,
    department_id: int | None = Dept,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await metrics_service.step_durations(session, days, department_id)


@router.get("/daily")
async def daily(
    days: int = Days,
    department_id: int | None = Dept,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await metrics_service.daily(session, days, department_id)


@router.get("/aging")
async def aging(
    department_id: int | None = Dept,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await metrics_service.aging(session, department_id)
