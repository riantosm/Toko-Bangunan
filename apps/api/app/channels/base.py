from abc import ABC, abstractmethod


class MessageChannel(ABC):
    @abstractmethod
    async def send_text(self, wa_id: str, text: str) -> None: ...
