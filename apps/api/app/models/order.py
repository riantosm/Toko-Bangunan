from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    intent: Mapped[str | None] = mapped_column(String(20), default=None)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, default=None)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), default=None, index=True
    )
    workflow_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("workflow_types.id"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), default=None)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit: Mapped[str] = mapped_column(String(20))
    raw_name: Mapped[str | None] = mapped_column(String(200), default=None)
    matched_score: Mapped[float | None] = mapped_column(Float, default=None)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product | None"] = relationship()
