from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RateCounter(Base):
    __tablename__ = "rate_counters"

    bucket_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
