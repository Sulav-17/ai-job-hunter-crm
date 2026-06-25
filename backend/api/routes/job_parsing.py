from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.mode import require_writable_mode
from backend.database.session import get_database_session
from backend.schemas.job_parser import JobParseResultResponse
from backend.services import job_parse_service, job_service

router = APIRouter(prefix="/jobs", tags=["job parsing"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
WritableMode = Annotated[None, Depends(require_writable_mode)]


@router.post("/{job_id}/parse", response_model=JobParseResultResponse)
def parse_job(job_id: int, db: DatabaseSession, _: WritableMode):
    result = job_parse_service.parse_and_persist_job(db, job_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return result


@router.get("/{job_id}/parse-result", response_model=JobParseResultResponse)
def get_job_parse_result(job_id: int, db: DatabaseSession):
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    result = job_parse_service.get_parse_result(db, job_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job has not been parsed",
        )
    return result
