from unittest.mock import AsyncMock

from app.core.config import settings
from app.routers import internal


async def test_wa_message_requires_secret(anon_client) -> None:
    r = await anon_client.post(
        "/internal/wa-message",
        json={"wa_id": "628x", "body": "halo"},
        headers={"X-Internal-Secret": "wrong"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


async def test_wa_message_enqueues(anon_client, monkeypatch) -> None:
    fake_queue = AsyncMock()
    monkeypatch.setattr(internal, "get_queue", AsyncMock(return_value=fake_queue))

    r = await anon_client.post(
        "/internal/wa-message",
        json={"wa_id": "628x", "body": "mau 2 sak semen", "name_hint": "A"},
        headers={"X-Internal-Secret": settings.internal_api_secret},
    )
    assert r.status_code == 202
    fake_queue.enqueue_job.assert_awaited_once()
    assert fake_queue.enqueue_job.await_args.args[0] == "process_wa_message"
