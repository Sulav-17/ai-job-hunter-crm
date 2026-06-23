from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.database.session import get_database_session
from backend.schemas.job import JobCreate, JobDetail, JobSummary, JobUpdate
from backend.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_job_or_404(db: Session, job_id: int):
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job


@router.post("", response_model=JobDetail, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: DatabaseSession):
    return job_service.create_job(db, payload)


@router.get("", response_model=list[JobSummary])
def list_jobs(db: DatabaseSession):
    return job_service.list_jobs(db)


@router.get("/{job_id}", response_model=JobDetail)
def retrieve_job(job_id: int, db: DatabaseSession):
    return get_job_or_404(db, job_id)


@router.patch("/{job_id}", response_model=JobDetail)
def update_job(job_id: int, payload: JobUpdate, db: DatabaseSession):
    job = get_job_or_404(db, job_id)
    return job_service.update_job(db, job, payload)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: DatabaseSession) -> Response:
    job = get_job_or_404(db, job_id)
    job_service.delete_job(db, job)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
