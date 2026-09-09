from app.core.config import settings


async def test_wa_message_requires_secret(anon_client) -> None:
    r = await anon_client.post(
        "/internal/wa-message",
        json={"wa_id": "628x", "body": "halo"},
        headers={"X-Internal-Secret": "wrong"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


async def test_wa_message_enqueues(anon_client, fake_task_queue) -> None:
    r = await anon_client.post(
        "/internal/wa-message",
        json={"wa_id": "628x", "body": "mau 2 sak semen", "name_hint": "A"},
        headers={"X-Internal-Secret": settings.internal_api_secret},
    )
    assert r.status_code == 202
    fake_task_queue.enqueue.assert_awaited_once()
    assert fake_task_queue.enqueue.await_args.args[0] == "process_wa_message"
