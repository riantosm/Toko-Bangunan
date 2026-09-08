from decimal import Decimal

import pytest_asyncio

from app.models.product import Product
from app.schemas.extraction import ExtractedItem, Extraction
from app.services import order_service


@pytest_asyncio.fixture
async def products(session) -> list[Product]:
    rows = [
        Product(
            sku="S-1", name="Semen Tiga Roda 40kg", unit="sak",
            price=62000, stock_qty=100,
        ),
        Product(
            sku="C-1", name="Cat Tembok Avitex Putih 5kg", unit="kaleng",
            price=95000, stock_qty=50,
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
            items=[
                ExtractedItem(name=n, quantity=Decimal(q), unit=u)
                for n, q, u in items
            ],
        )

    return inner


async def test_intake_matches_products(client, products, monkeypatch) -> None:
    monkeypatch.setattr(
        order_service,
        "extract_order",
        _fake("order", [("semen tiga roda", "3", "sak"),
                        ("cat putih avitex", "2", "kaleng")], 0.95),
    )
    r = await client.post(
        "/orders/intake", json={"customer_name": "Andi", "body": "x"}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["needs_review"] is False
    assert all(i["product_id"] is not None for i in body["items"])
    assert body["items"][0]["raw_name"] == "semen tiga roda"


async def test_intake_flags_review_on_unmatched(client, products, monkeypatch) -> None:
    monkeypatch.setattr(
        order_service,
        "extract_order",
        _fake("order", [("barang ngawur zzz", "1", "pcs")], 0.9),
    )
    r = await client.post(
        "/orders/intake", json={"customer_name": "Andi", "body": "x"}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["needs_review"] is True
    assert body["items"][0]["product_id"] is None


async def test_intake_flags_review_on_inquiry(client, products, monkeypatch) -> None:
    monkeypatch.setattr(
        order_service,
        "extract_order",
        _fake("inquiry", [("semen tiga roda", "1", "sak")], 0.9),
    )
    r = await client.post(
        "/orders/intake", json={"customer_name": "Andi", "body": "x"}
    )
    assert r.json()["needs_review"] is True


async def test_intake_flags_review_on_low_confidence(client, products, monkeypatch) -> None:
    monkeypatch.setattr(
        order_service,
        "extract_order",
        _fake("order", [("semen tiga roda", "1", "sak")], 0.4),
    )
    r = await client.post(
        "/orders/intake", json={"customer_name": "Andi", "body": "x"}
    )
    assert r.json()["needs_review"] is True
