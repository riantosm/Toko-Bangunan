from datetime import date

from fastapi import APIRouter, Depends, Header, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.errors import UnauthorizedError
from app.core.taskqueue import get_task_queue
from app.reports.daily import run_daily_report

router = APIRouter(prefix="/internal", tags=["internal"])


def _check_secret(secret: str) -> None:
    if secret != settings.internal_api_secret:
        raise UnauthorizedError("bad internal secret")


class WaMessageIn(BaseModel):
    wa_id: str
    body: str
    name_hint: str = ""
    wa_message_id: str | None = None


@router.post("/wa-message", status_code=status.HTTP_202_ACCEPTED)
async def wa_message(
    payload: WaMessageIn,
    x_internal_secret: str = Header(default=""),
) -> dict[str, str]:
    _check_secret(x_internal_secret)
    await get_task_queue().enqueue(
        "process_wa_message", payload.wa_id, payload.body, payload.name_hint
    )
    return {"status": "queued"}


@router.post("/nightly-report")
async def nightly_report(
    day: date | None = Query(default=None, alias="date"),
    force: bool = Query(default=False),
    x_internal_secret: str = Header(default=""),
    session: AsyncSession = Depends(get_session),
) -> dict:
    _check_secret(x_internal_secret)
    return await run_daily_report(session, day, force=force)
