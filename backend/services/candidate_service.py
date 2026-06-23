from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models.candidate import CandidateProfile
from backend.schemas.candidate import CandidateCreate, CandidateUpdate


def create_candidate(db: Session, payload: CandidateCreate) -> CandidateProfile:
    candidate = CandidateProfile(**payload.model_dump())
    db.add(candidate)

    try:
        db.commit()
        db.refresh(candidate)
    except SQLAlchemyError:
        db.rollback()
        raise

    return candidate


def list_candidates(db: Session) -> Sequence[CandidateProfile]:
    statement = select(CandidateProfile).order_by(CandidateProfile.id.asc())
    return db.scalars(statement).all()


def get_candidate(db: Session, candidate_id: int) -> CandidateProfile | None:
    return db.get(CandidateProfile, candidate_id)


def update_candidate(
    db: Session,
    candidate: CandidateProfile,
    payload: CandidateUpdate,
) -> CandidateProfile:
    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(candidate, field_name, value)

    try:
        db.commit()
        db.refresh(candidate)
    except SQLAlchemyError:
        db.rollback()
        raise

    return candidate


def delete_candidate(db: Session, candidate: CandidateProfile) -> None:
    db.delete(candidate)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
