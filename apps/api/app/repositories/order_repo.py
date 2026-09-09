from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order


async def get_by_id(session: AsyncSession, order_id: int) -> Order | None:
    stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    return await session.scalar(stmt)


async def list_paginated(session: AsyncSession, page: int, size: int) -> tuple[list[Order], int]:
    total = await session.scalar(select(func.count()).select_from(Order)) or 0
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.id.desc())
        .limit(size)
        .offset((page - 1) * size)
    )
    rows = (await session.scalars(stmt)).all()
    return list(rows), total
