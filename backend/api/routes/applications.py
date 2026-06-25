from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.core.mode import require_writable_mode
from backend.database.session import get_database_session
from backend.schemas.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationStatusHistoryResponse,
    ApplicationSummary,
    ApplicationUpdate,
)
from backend.services import application_service

router = APIRouter(prefix="/applications", tags=["applications"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
WritableMode = Annotated[None, Depends(require_writable_mode)]


@router.post(
    "",
    response_model=ApplicationDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_application(payload: ApplicationCreate, db: DatabaseSession, _: WritableMode):
    try:
        return application_service.create_application(db, payload)
    except application_service.CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        ) from exc
    except application_service.JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        ) from exc
    except application_service.DuplicateApplicationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application already exists for this candidate and job",
        ) from exc


@router.get("", response_model=list[ApplicationSummary])
def list_applications(db: DatabaseSession):
    return application_service.list_applications(db)


@router.get("/{application_id}", response_model=ApplicationDetail)
def retrieve_application(application_id: int, db: DatabaseSession):
    try:
        return application_service.get_application_or_raise(db, application_id)
    except application_service.ApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        ) from exc


@router.patch("/{application_id}", response_model=ApplicationDetail)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    db: DatabaseSession,
    _: WritableMode,
):
    try:
        return application_service.update_application(db, application_id, payload)
    except application_service.ApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        ) from exc


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: int, db: DatabaseSession, _: WritableMode) -> Response:
    try:
        application_service.delete_application(db, application_id)
    except application_service.ApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{application_id}/status-history",
    response_model=list[ApplicationStatusHistoryResponse],
)
def list_status_history(application_id: int, db: DatabaseSession):
    try:
        return application_service.list_status_history(db, application_id)
    except application_service.ApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        ) from exc
