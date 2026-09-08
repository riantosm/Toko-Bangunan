from datetime import datetime

from pydantic import BaseModel


class WorkflowStepRead(BaseModel):
    id: int
    order_id: int
    seq: int
    step_type_name: str
    assigned_at: datetime | None
    completed_at: datetime | None
    outcome: str | None
    sla_target_minutes: int
    elapsed_minutes: float | None


class CompleteStepRequest(BaseModel):
    outcome: str = "approved"
