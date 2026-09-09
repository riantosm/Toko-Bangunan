from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0)


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderIntakeRequest(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1)


class OrderIntakeResponse(BaseModel):
    job_id: str


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    raw_name: str | None
    quantity: Decimal
    unit: str
    matched_score: float | None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    status: str
    intent: str | None
    extraction_confidence: float | None
    needs_review: bool
    created_at: datetime
    items: list[OrderItemRead]


class OrderListRow(BaseModel):
    id: int
    customer_name: str
    status: str
    needs_review: bool
    item_count: int
    created_at: datetime


class OrderListResponse(BaseModel):
    items: list[OrderListRow]
    next_cursor: int | None = None
