from decimal import Decimal
from unittest.mock import AsyncMock

import pytest_asyncio

from app.models.job import Job
from app.models.product import Product
from app.repositories import order_repo
from app.schemas.extraction import ExtractedItem, Extraction
from app.services import order_service
from app.services.extraction import ExtractionError


@pytest_asyncio.fixture
async def products(session) -> list[Product]:
    rows = [
        Product(
            sku="S-1",
            name="Semen Tiga Roda 40kg",
            unit="sak",
            price=62000,
            stock_qty=100,
        ),
        Product(
            sku="C-1",
            name="Cat Tembok Avitex Putih 5kg",
            unit="kaleng",
            price=95000,
            stock_qty=50,
        ),
    ]
    session.add_all(rows)
    await session.commit()
    return rows


def _fake(intent: str, items: list[tuple[str, str, str]], confidence: float):
    async def inner(body: str) -> Extraction:
        return Extraction(
            intent=intent,
            confidence=confidence,
            items=[ExtractedItem(name=n, quantity=Decimal(q), unit=u) for n, q, u in items],
        )

    return inner


async def _make_job(session) -> Job:
    job = Job(type="order_intake", status="queued", progress=0)
    session.add(job)
    await session.commit()
    return job


async def test_run_intake_matches_products(session, products, monkeypatch) -> None:
    monkeypatch.setattr(
        order_service,
        "extract_order",
        _fake(
            "order", [("semen tiga roda", "3", "sak"), ("cat putih avitex", "2", "kaleng")], 0.95
        ),
    )
    job = await _make_job(session)
    await order_service.run_intake(session, job.id, "Andi", "x")
    await session.refresh(job)

    assert job.status == "done"
    assert job.progress == 100
    order = await order_repo.get_by_id(session, int(job.result_ref))
    assert order is not None
    assert order.needs_review is False
    assert all(i.product_id is not None for i in order.items)


async def test_run_intake_flags_review_on_unmatched(session, products, monkeypatch) -> None:
    monkeypatch.setattr(
        order_service,
        "extract_order",
        _fake("order", [("barang ngawur zzz", "1", "pcs")], 0.9),
    )
    job = await _make_job(session)
    await order_service.run_intake(session, job.id, "Andi", "x")
    await session.refresh(job)

    order = await order_repo.get_by_id(session, int(job.result_ref))
    assert order is not None
    assert order.needs_review is True
    assert order.items[0].product_id is None


async def test_run_intake_sets_error_on_extraction_failure(session, monkeypatch) -> None:
    async def boom(body: str) -> Extraction:
        raise ExtractionError("json invalid")

    monkeypatch.setattr(order_service, "extract_order", boom)
    job = await _make_job(session)
    await order_service.run_intake(session, job.id, "Andi", "x")
    await session.refresh(job)

    assert job.status == "error"
    assert job.error


async def test_intake_endpoint_returns_202(client, monkeypatch) -> None:
    fake_queue = AsyncMock()
    monkeypatch.setattr(order_service, "get_queue", AsyncMock(return_value=fake_queue))
    r = await client.post("/orders/intake", json={"customer_name": "Andi", "body": "x"})
    assert r.status_code == 202
    assert "job_id" in r.json()
    fake_queue.enqueue_job.assert_awaited_once()


async def test_intake_endpoint_is_idempotent(client, monkeypatch) -> None:
    fake_queue = AsyncMock()
    monkeypatch.setattr(order_service, "get_queue", AsyncMock(return_value=fake_queue))
    headers = {"Idempotency-Key": "key-abc-123"}
    body = {"customer_name": "Andi", "body": "x"}

    r1 = await client.post("/orders/intake", json=body, headers=headers)
    r2 = await client.post("/orders/intake", json=body, headers=headers)

    assert r1.status_code == 202
    assert r1.json()["job_id"] == r2.json()["job_id"]
    assert fake_queue.enqueue_job.await_count == 1
