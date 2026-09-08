from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal["order", "inquiry", "complaint"]


class ExtractedItem(BaseModel):
    name: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit: str = Field(min_length=1)


class Extraction(BaseModel):
    intent: Intent
    items: list[ExtractedItem]
    confidence: float = Field(ge=0, le=1)
    notes: str = ""
