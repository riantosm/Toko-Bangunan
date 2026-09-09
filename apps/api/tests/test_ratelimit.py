from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.config import settings
from app.services import order_service


async def test_intake_rate_limited(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_intake_per_min", 3)
    monkeypatch.setattr(
        order_service, "get_queue", AsyncMock(return_value=AsyncMock())
    )

    codes = []
    for _ in range(5):
        r = await client.post(
            "/orders/intake",
            json={"customer_name": "A", "body": "x"},
            headers={"Idempotency-Key": str(uuid4())},
        )
        codes.append(r.status_code)

    assert codes.count(202) == 3
    assert codes.count(429) == 2

    r = await client.post(
        "/orders/intake",
        json={"customer_name": "A", "body": "x"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 429
    assert "retry-after" in {k.lower() for k in r.headers}
    assert r.json()["error"]["code"] == "rate_limited"
    assert r.headers["X-RateLimit-Limit"] == "3"
