from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0)


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: Decimal
    unit: str


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    status: str
    created_at: datetime
    items: list[OrderItemRead]


class OrderListRow(BaseModel):
    id: int
    customer_name: str
    status: str
    created_at: datetime
    item_count: int


class OrderListResponse(BaseModel):
    items: list[OrderListRow]
    total: int
    page: int
    size: int
