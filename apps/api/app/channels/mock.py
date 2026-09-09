import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import MessageChannel
from app.models.raw_message import RawMessage

logger = logging.getLogger("app.channel")


class MockChannel(MessageChannel):
    """Dev channel: persist the outbound reply so the simulator can show it."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def send_text(self, wa_id: str, text: str) -> None:
        self.session.add(
            RawMessage(
                channel="whatsapp", wa_id=wa_id, direction="out", body=text
            )
        )
        await self.session.flush()
        logger.info("wa reply -> %s: %s", wa_id, text[:80])
