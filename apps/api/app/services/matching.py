from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

MATCH_THRESHOLD = 0.3


async def match_product(session: AsyncSession, raw_name: str) -> tuple[Product | None, float]:
    score_col = func.similarity(Product.name, raw_name)
    stmt = select(Product, score_col.label("score")).order_by(score_col.desc()).limit(1)
    row = (await session.execute(stmt)).first()
    if row is None:
        return None, 0.0
    product, score = row
    score = float(score or 0.0)
    if score < MATCH_THRESHOLD:
        return None, score
    return product, score
