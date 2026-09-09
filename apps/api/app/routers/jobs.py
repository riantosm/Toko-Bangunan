from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.job import Job
from app.schemas.job import JobRead

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)) -> Job:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job tidak ditemukan")
    return job
