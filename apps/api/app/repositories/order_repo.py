from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order


async def get_by_id(session: AsyncSession, order_id: int) -> Order | None:
    stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    return await session.scalar(stmt)


async def list_keyset(
    session: AsyncSession, limit: int, after: int | None
) -> list[Order]:
    """Keyset pagination on the PK (newest first). `after` = last id from the
    previous page; PostgreSQL seeks straight to it via `orders_pkey` — no OFFSET,
    so cost stays flat no matter how deep the page. See db_lab/NOTES.md scenario D.
    """
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.id.desc())
        .limit(limit)
    )
    if after is not None:
        stmt = stmt.where(Order.id < after)
    rows = (await session.scalars(stmt)).all()
    return list(rows)
