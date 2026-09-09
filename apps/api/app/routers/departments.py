from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.department import Department

router = APIRouter(
    prefix="/departments",
    tags=["departments"],
    dependencies=[Depends(get_current_user)],
)


class DepartmentRead(BaseModel):
    id: int
    name: str


@router.get("", response_model=list[DepartmentRead])
async def list_departments(
    session: AsyncSession = Depends(get_session),
) -> list[Department]:
    rows = await session.scalars(select(Department).order_by(Department.name))
    return list(rows)
