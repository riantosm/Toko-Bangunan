from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ReportRun(Base):
    __tablename__ = "report_runs"

    report_date: Mapped[date] = mapped_column(Date, primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    message_id: Mapped[str | None] = mapped_column(String(120), default=None)
