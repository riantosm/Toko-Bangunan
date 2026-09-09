from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import MessageChannel
from app.channels.mock import MockChannel
from app.channels.whatsapp import WhatsAppChannel
from app.core.config import settings

__all__ = ["MessageChannel", "MockChannel", "WhatsAppChannel", "get_channel"]


def get_channel(session: AsyncSession) -> MessageChannel:
    if settings.whatsapp_token and settings.whatsapp_phone_number_id:
        return WhatsAppChannel()
    return MockChannel(session)
