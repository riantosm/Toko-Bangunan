from decimal import Decimal

import pytest_asyncio
from sqlalchemy import select

from app.models.conversation import Conversation
from app.models.order import Order
from app.models.product import Product
from app.models.raw_message import RawMessage
from app.models.workflow import StepType
from app.repositories import order_repo
from app.schemas.extraction import ExtractedItem, Extraction
from app.services import conversation_service
from app.services.extraction import ExtractionError

WA = "628000111222"


@pytest_asyncio.fixture
async def catalog(session) -> None:
    session.add_all(
        [
            Product(
                sku="S-1", name="Semen Tiga Roda 40kg", unit="sak",
                price=62000, stock_qty=100,
            ),
            Product(
                sku="C-1", name="Cat Tembok Avitex Putih 5kg", unit="kaleng",
                price=95000, stock_qty=50,
            ),
            StepType(name="Verifikasi Stok", seq=1, default_sla_minutes=60),
            StepType(name="Approval Manajer", seq=2, default_sla_minutes=240),
            StepType(name="Konfirmasi Pembayaran", seq=3, default_sla_minutes=120),
        ]
    )
    await session.commit()


def _fake(intent: str, items: list[tuple[str, str, str]], confidence: float = 0.95):
    async def inner(body: str) -> Extraction:
        return Extraction(
            intent=intent,
            confidence=confidence,
            items=[
                ExtractedItem(name=n, quantity=Decimal(q), unit=u) for n, q, u in items
            ],
        )

    return inner


async def _messages(session) -> list[RawMessage]:
    return list(
        await session.scalars(
            select(RawMessage).where(RawMessage.wa_id == WA).order_by(RawMessage.id)
        )
    )


async def test_first_message_creates_draft(session, catalog, monkeypatch) -> None:
    monkeypatch.setattr(
        conversation_service,
        "extract_order",
        _fake("order", [("semen tiga roda", "3", "sak")]),
    )
    reply = await conversation_service.handle_incoming(
        session, wa_id=WA, body="mau 3 sak semen", name_hint="Budi"
    )
    await session.commit()

    conv = await session.get(Conversation, WA)
    assert conv is not None
    assert conv.customer_name == "Budi"
    assert conv.active_order_id is not None

    order = await session.get(Order, conv.active_order_id)
    assert order.status == "draft"
    assert "Semen Tiga Roda" in reply
    assert [m.direction for m in await _messages(session)] == ["in", "out"]


async def test_second_message_merges_into_same_draft(
    session, catalog, monkeypatch
) -> None:
    monkeypatch.setattr(
        conversation_service,
        "extract_order",
        _fake("order", [("semen tiga roda", "3", "sak")]),
    )
    await conversation_service.handle_incoming(session, wa_id=WA, body="a")
    await session.commit()
    conv = await session.get(Conversation, WA)
    first_order_id = conv.active_order_id

    monkeypatch.setattr(
        conversation_service,
        "extract_order",
        _fake("order", [("cat putih avitex", "2", "kaleng")]),
    )
    await conversation_service.handle_incoming(session, wa_id=WA, body="b")
    await session.commit()

    await session.refresh(conv)
    assert conv.active_order_id == first_order_id

    order = await order_repo.get_by_id(session, first_order_id)
    assert order is not None
    assert len(order.items) == 2


async def test_konfirmasi_runs_workflow(session, catalog, monkeypatch) -> None:
    monkeypatch.setattr(
        conversation_service,
        "extract_order",
        _fake("order", [("semen tiga roda", "1", "sak")]),
    )
    await conversation_service.handle_incoming(session, wa_id=WA, body="a")
    await session.commit()
    conv = await session.get(Conversation, WA)
    order_id = conv.active_order_id

    reply = await conversation_service.handle_incoming(
        session, wa_id=WA, body="KONFIRMASI"
    )
    await session.commit()

    await session.refresh(conv)
    assert conv.active_order_id is None
    order = await session.get(Order, order_id)
    assert order.status == "confirmed"
    assert f"#{order_id}" in reply


async def test_inquiry_does_not_create_draft(session, catalog, monkeypatch) -> None:
    monkeypatch.setattr(
        conversation_service,
        "extract_order",
        _fake("inquiry", [("triplek", "1", "lembar")]),
    )
    await conversation_service.handle_incoming(
        session, wa_id=WA, body="triplek 9mm ada?"
    )
    await session.commit()

    conv = await session.get(Conversation, WA)
    assert conv is not None
    assert conv.active_order_id is None


async def test_extraction_error_gives_apology(session, catalog, monkeypatch) -> None:
    async def boom(body: str) -> Extraction:
        raise ExtractionError("bad json")

    monkeypatch.setattr(conversation_service, "extract_order", boom)
    reply = await conversation_service.handle_incoming(
        session, wa_id=WA, body="asdkjh qwe"
    )
    await session.commit()

    assert "tulis ulang" in reply.lower()
    conv = await session.get(Conversation, WA)
    assert conv.active_order_id is None
