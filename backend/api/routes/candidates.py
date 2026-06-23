from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.database.session import get_database_session
from backend.schemas.candidate import (
    CandidateCreate,
    CandidateDetail,
    CandidateSummary,
    CandidateUpdate,
)
from backend.services import candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_candidate_or_404(db: Session, candidate_id: int):
    candidate = candidate_service.get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    return candidate


@router.post("", response_model=CandidateDetail, status_code=status.HTTP_201_CREATED)
def create_candidate(payload: CandidateCreate, db: DatabaseSession):
    return candidate_service.create_candidate(db, payload)


@router.get("", response_model=list[CandidateSummary])
def list_candidates(db: DatabaseSession):
    return candidate_service.list_candidates(db)


@router.get("/{candidate_id}", response_model=CandidateDetail)
def retrieve_candidate(candidate_id: int, db: DatabaseSession):
    return get_candidate_or_404(db, candidate_id)


@router.patch("/{candidate_id}", response_model=CandidateDetail)
def update_candidate(candidate_id: int, payload: CandidateUpdate, db: DatabaseSession):
    candidate = get_candidate_or_404(db, candidate_id)
    return candidate_service.update_candidate(db, candidate, payload)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(candidate_id: int, db: DatabaseSession) -> Response:
    candidate = get_candidate_or_404(db, candidate_id)
    candidate_service.delete_candidate(db, candidate)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
