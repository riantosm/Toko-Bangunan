from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.product import Product
from app.schemas.product import ProductRead

router = APIRouter(
    prefix="/products",
    tags=["products"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[ProductRead])
async def list_products(session: AsyncSession = Depends(get_session)) -> list[Product]:
    rows = (await session.scalars(select(Product).order_by(Product.name))).all()
    return list(rows)
