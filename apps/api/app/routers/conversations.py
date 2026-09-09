from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.raw_message import RawMessage

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(get_current_user)],
)


class MessageRead(BaseModel):
    id: int
    direction: str
    body: str
    created_at: datetime


@router.get("/{wa_id}/messages", response_model=list[MessageRead])
async def list_messages(
    wa_id: str, session: AsyncSession = Depends(get_session)
) -> list[RawMessage]:
    rows = await session.scalars(
        select(RawMessage)
        .where(RawMessage.wa_id == wa_id)
        .order_by(RawMessage.id)
    )
    return list(rows)
