import httpx

from app.channels.base import MessageChannel
from app.core.config import settings


class WhatsAppChannel(MessageChannel):
    async def send_text(self, wa_id: str, text: str) -> None:
        url = (
            f"https://graph.facebook.com/v21.0/"
            f"{settings.whatsapp_phone_number_id}/messages"
        )
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": wa_id,
                    "type": "text",
                    "text": {"body": text},
                },
            )
        resp.raise_for_status()
