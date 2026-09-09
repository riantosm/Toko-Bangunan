from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.channels import get_channel
from app.models.conversation import Conversation
from app.models.order import Order, OrderItem
from app.models.raw_message import RawMessage
from app.services.extraction import ExtractionError, extract_order
from app.services.matching import match_product
from app.services.workflow_service import confirm_order

CONFIRM_KEYWORDS = {"konfirmasi", "ok", "oke", "iya", "ya", "setuju"}


async def _get_or_create_conversation(
    session: AsyncSession, wa_id: str, name_hint: str
) -> Conversation:
    conv = await session.get(Conversation, wa_id)
    if conv is None:
        conv = Conversation(
            wa_id=wa_id, customer_name=name_hint or f"WA {wa_id[-4:]}"
        )
        session.add(conv)
        await session.flush()
    return conv


async def _ensure_draft(session: AsyncSession, conv: Conversation) -> Order:
    if conv.active_order_id is not None:
        order = await session.scalar(
            select(Order)
            .where(Order.id == conv.active_order_id)
            .options(selectinload(Order.items))
        )
        if order is not None and order.status == "draft":
            return order

    order = Order(
        customer_name=conv.customer_name, status="draft", intent="order", items=[]
    )
    session.add(order)
    await session.flush()
    conv.active_order_id = order.id
    return order


async def _send(session: AsyncSession, wa_id: str, text: str) -> None:
    await get_channel(session).send_text(wa_id, text)


async def handle_incoming(
    session: AsyncSession, *, wa_id: str, body: str, name_hint: str = ""
) -> str:
    session.add(
        RawMessage(channel="whatsapp", wa_id=wa_id, direction="in", body=body)
    )
    conv = await _get_or_create_conversation(session, wa_id, name_hint)

    if body.strip().lower() in CONFIRM_KEYWORDS and conv.active_order_id is not None:
        order = await confirm_order(session, conv.active_order_id)
        conv.active_order_id = None
        reply = (
            f"Order #{order.id} dikonfirmasi dan sedang kami proses. Terima kasih!"
        )
        await _send(session, wa_id, reply)
        return reply

    try:
        extraction = await extract_order(body)
    except ExtractionError:
        reply = "Maaf, pesannya belum terbaca jelas. Bisa tulis ulang barang dan jumlahnya?"
        await _send(session, wa_id, reply)
        return reply

    if extraction.intent != "order" or not extraction.items:
        reply = (
            "Baik, dicatat. Kalau mau memesan, sebutkan barang dan jumlahnya ya "
            "(contoh: 3 sak semen)."
        )
        await _send(session, wa_id, reply)
        return reply

    order = await _ensure_draft(session, conv)
    lines: list[str] = []
    for ex in extraction.items:
        product, score = await match_product(session, ex.name)
        order.items.append(
            OrderItem(
                product_id=product.id if product else None,
                raw_name=ex.name,
                quantity=ex.quantity,
                unit=product.unit if product else ex.unit,
                matched_score=score,
            )
        )
        unit = product.unit if product else ex.unit
        label = product.name if product else f"{ex.name} (perlu dicek admin)"
        lines.append(f"- {ex.quantity} {unit} {label}")
    await session.flush()

    reply = (
        "Baik, dicatat:\n"
        + "\n".join(lines)
        + f"\n\nTotal {len(order.items)} item di order #{order.id}. "
        + "Balas KONFIRMASI untuk memproses."
    )
    await _send(session, wa_id, reply)
    return reply
