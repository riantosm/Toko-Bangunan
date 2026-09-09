from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.taskqueue import get_task_queue
from app.models.job import Job
from app.models.order import Order, OrderItem
from app.models.processed_request import ProcessedRequest
from app.models.product import Product
from app.repositories import order_repo
from app.schemas.order import OrderCreate, OrderListResponse, OrderListRow
from app.services.extraction import ExtractionError, extract_order
from app.services.matching import match_product

CONFIDENCE_THRESHOLD = 0.6


async def create_order(session: AsyncSession, payload: OrderCreate) -> Order:
    product_ids = {i.product_id for i in payload.items}
    products = {
        p.id: p for p in await session.scalars(select(Product).where(Product.id.in_(product_ids)))
    }
    missing = product_ids - products.keys()
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"produk tidak ditemukan: {sorted(missing)}",
        )

    order = Order(customer_name=payload.customer_name, status="draft")
    for item in payload.items:
        product = products[item.product_id]
        order.items.append(
            OrderItem(product_id=product.id, quantity=item.quantity, unit=product.unit)
        )
    session.add(order)
    await session.commit()

    created = await order_repo.get_by_id(session, order.id)
    assert created is not None
    return created


async def enqueue_intake(
    session: AsyncSession,
    customer_name: str,
    body: str,
    idempotency_key: str | None = None,
) -> Job:
    if idempotency_key:
        seen = await session.get(ProcessedRequest, idempotency_key)
        if seen is not None:
            existing = await session.get(Job, seen.response["job_id"])
            if existing is not None:
                return existing

    job = Job(type="order_intake", status="queued", progress=0)
    session.add(job)
    await session.flush()

    if idempotency_key:
        session.add(ProcessedRequest(key=idempotency_key, response={"job_id": job.id}))

    await session.commit()

    await get_task_queue().enqueue("process_intake_job", job.id, customer_name, body)
    return job


async def run_intake(session: AsyncSession, job_id: str, customer_name: str, body: str) -> None:
    job = await session.get(Job, job_id)
    if job is None:
        return

    job.status = "processing"
    job.progress = 10
    await session.commit()

    try:
        extraction = await extract_order(body)
    except ExtractionError as exc:
        job.status = "error"
        job.error = f"AI gagal memproses pesan: {exc}"[:500]
        job.progress = 100
        await session.commit()
        return

    job.progress = 50
    await session.commit()

    order = Order(
        customer_name=customer_name,
        status="draft",
        intent=extraction.intent,
        extraction_confidence=extraction.confidence,
    )
    has_unmatched = False
    for ex_item in extraction.items:
        product, score = await match_product(session, ex_item.name)
        if product is None:
            has_unmatched = True
        order.items.append(
            OrderItem(
                product_id=product.id if product else None,
                raw_name=ex_item.name,
                quantity=ex_item.quantity,
                unit=product.unit if product else ex_item.unit,
                matched_score=score,
            )
        )

    order.needs_review = (
        extraction.confidence < CONFIDENCE_THRESHOLD
        or has_unmatched
        or extraction.intent != "order"
    )
    session.add(order)
    await session.commit()

    job.status = "done"
    job.result_ref = str(order.id)
    job.progress = 100
    await session.commit()


async def get_order(session: AsyncSession, order_id: int) -> Order:
    order = await order_repo.get_by_id(session, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order tidak ditemukan")
    return order


async def list_orders(
    session: AsyncSession, limit: int, after: int | None
) -> OrderListResponse:
    rows = await order_repo.list_keyset(session, limit, after)
    # full page returned -> there may be more; cursor = id of the last row
    next_cursor = rows[-1].id if len(rows) == limit else None
    return OrderListResponse(
        items=[
            OrderListRow(
                id=o.id,
                customer_name=o.customer_name,
                status=o.status,
                needs_review=o.needs_review,
                item_count=len(o.items),
                created_at=o.created_at,
            )
            for o in rows
        ],
        next_cursor=next_cursor,
    )
