from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.deps import require_role
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.services import metrics_service

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    dependencies=[Depends(require_role("manager", "admin"))],
)

Days = Query(30, ge=1, le=365)


@router.get("/summary")
async def summary(
    days: int = Days, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    return await metrics_service.summary(session, days)


@router.get("/step-durations")
async def step_durations(
    days: int = Days, session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    return await metrics_service.step_durations(session, days)


@router.get("/daily")
async def daily(
    days: int = Days, session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    return await metrics_service.daily(session, days)


@router.get("/aging")
async def aging(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await metrics_service.aging(session)
