from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.session import get_database_session
from backend.schemas.candidate_parser import CandidateParseResultResponse
from backend.services import candidate_parse_service, candidate_service

router = APIRouter(prefix="/candidates", tags=["candidate parsing"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post("/{candidate_id}/parse", response_model=CandidateParseResultResponse)
def parse_candidate(candidate_id: int, db: DatabaseSession):
    try:
        result = candidate_parse_service.parse_and_persist_candidate(db, candidate_id)
    except candidate_parse_service.MissingResumeTextError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate resume text is required",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    return result


@router.get("/{candidate_id}/parse-result", response_model=CandidateParseResultResponse)
def get_candidate_parse_result(candidate_id: int, db: DatabaseSession):
    candidate = candidate_service.get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )

    result = candidate_parse_service.get_parse_result(db, candidate_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate has not been parsed",
        )
    return result
