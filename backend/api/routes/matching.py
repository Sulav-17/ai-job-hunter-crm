from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.session import get_database_session
from backend.schemas.matching import MatchResultResponse
from backend.services import match_service

router = APIRouter(prefix="/candidates", tags=["matching"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post(
    "/{candidate_id}/jobs/{job_id}/match",
    response_model=MatchResultResponse,
)
def calculate_match(candidate_id: int, job_id: int, db: DatabaseSession):
    try:
        return match_service.calculate_and_persist_match(db, candidate_id, job_id)
    except match_service.CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        ) from exc
    except match_service.JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        ) from exc
    except match_service.CandidateUnparsedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate must be parsed before matching",
        ) from exc
    except match_service.JobUnparsedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job must be parsed before matching",
        ) from exc


@router.get(
    "/{candidate_id}/jobs/{job_id}/match-result",
    response_model=MatchResultResponse,
)
def get_match_result(candidate_id: int, job_id: int, db: DatabaseSession):
    try:
        return match_service.get_saved_match_result(db, candidate_id, job_id)
    except match_service.CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        ) from exc
    except match_service.JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        ) from exc
    except match_service.MatchResultNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match result not found",
        ) from exc
