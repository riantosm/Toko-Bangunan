from datetime import datetime

from sqlalchemy import (
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class StepType(Base):
    __tablename__ = "step_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    seq: Mapped[int] = mapped_column(Integer)
    default_sla_minutes: Mapped[int] = mapped_column(Integer)


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (
        Index("ix_ws_steptype_assigned", "step_type_id", "assigned_at"),
        # pending steps: the aging query filters assigned_at IS NOT NULL AND
        # completed_at IS NULL, then orders by assigned_at
        Index(
            "ix_ws_pending",
            "assignee_id",
            "assigned_at",
            postgresql_where=text("completed_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    step_type_id: Mapped[int] = mapped_column(ForeignKey("step_types.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    outcome: Mapped[str | None] = mapped_column(String(20), default=None)
    sla_target_minutes: Mapped[int] = mapped_column(Integer)

    elapsed_minutes: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        Computed(
            "EXTRACT(EPOCH FROM (completed_at - assigned_at)) / 60",
            persisted=True,
        ),
    )

    step_type: Mapped["StepType"] = relationship()
