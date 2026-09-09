from fastapi import APIRouter, Header, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.core.taskqueue import get_task_queue

router = APIRouter(prefix="/internal", tags=["internal"])


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
    if x_internal_secret != settings.internal_api_secret:
        raise UnauthorizedError("bad internal secret")
    await get_task_queue().enqueue(
        "process_wa_message", payload.wa_id, payload.body, payload.name_hint
    )
    return {"status": "queued"}
