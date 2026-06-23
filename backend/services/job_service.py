from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models.job import JobPosting
from backend.schemas.job import JobCreate, JobUpdate


def create_job(db: Session, payload: JobCreate) -> JobPosting:
    job = JobPosting(**payload.model_dump())
    db.add(job)

    try:
        db.commit()
        db.refresh(job)
    except SQLAlchemyError:
        db.rollback()
        raise

    return job


def list_jobs(db: Session) -> Sequence[JobPosting]:
    statement = select(JobPosting).order_by(JobPosting.id.desc())
    return db.scalars(statement).all()


def get_job(db: Session, job_id: int) -> JobPosting | None:
    return db.get(JobPosting, job_id)


def update_job(db: Session, job: JobPosting, payload: JobUpdate) -> JobPosting:
    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(job, field_name, value)

    try:
        db.commit()
        db.refresh(job)
    except SQLAlchemyError:
        db.rollback()
        raise

    return job


def delete_job(db: Session, job: JobPosting) -> None:
    db.delete(job)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
