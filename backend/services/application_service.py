from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models.application import Application, ApplicationStatusHistory
from backend.models.candidate import CandidateProfile
from backend.models.job import JobPosting
from backend.schemas.application import ApplicationCreate, ApplicationUpdate


class ApplicationNotFoundError(ValueError):
    pass


class CandidateNotFoundError(ValueError):
    pass


class JobNotFoundError(ValueError):
    pass


class DuplicateApplicationError(ValueError):
    pass


def create_application(db: Session, payload: ApplicationCreate) -> Application:
    _get_candidate_or_raise(db, payload.candidate_id)
    _get_job_or_raise(db, payload.job_id)
    if _get_application_by_candidate_job(db, payload.candidate_id, payload.job_id):
        raise DuplicateApplicationError(
            "Application already exists for this candidate and job",
        )

    application = Application(**payload.model_dump())
    try:
        db.add(application)
        db.flush()
        db.add(
            ApplicationStatusHistory(
                application_id=application.id,
                previous_status=None,
                new_status=application.status,
            ),
        )
        db.commit()
        db.refresh(application)
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate_candidate_job_error(exc):
            raise DuplicateApplicationError(
                "Application already exists for this candidate and job",
            ) from exc
        raise
    except SQLAlchemyError:
        db.rollback()
        raise

    return application


def list_applications(db: Session) -> Sequence[Application]:
    statement = select(Application).order_by(Application.id.desc())
    return db.scalars(statement).all()


def get_application(db: Session, application_id: int) -> Application | None:
    return db.get(Application, application_id)


def get_application_or_raise(db: Session, application_id: int) -> Application:
    application = get_application(db, application_id)
    if application is None:
        raise ApplicationNotFoundError("Application not found")
    return application


def update_application(
    db: Session,
    application_id: int,
    payload: ApplicationUpdate,
) -> Application:
    application = get_application_or_raise(db, application_id)
    updates = payload.model_dump(exclude_unset=True)
    previous_status = application.status
    supplied_status = updates.get("status")
    status_changed = supplied_status is not None and supplied_status != previous_status

    for field_name, value in updates.items():
        setattr(application, field_name, value)

    if (
        status_changed
        and supplied_status == "applied"
        and "applied_at" not in updates
        and application.applied_at is None
    ):
        application.applied_at = func.now()

    if status_changed:
        db.add(
            ApplicationStatusHistory(
                application_id=application.id,
                previous_status=previous_status,
                new_status=supplied_status,
            ),
        )

    try:
        db.commit()
        db.refresh(application)
    except SQLAlchemyError:
        db.rollback()
        raise

    return application


def delete_application(db: Session, application_id: int) -> None:
    application = get_application_or_raise(db, application_id)
    db.delete(application)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def list_status_history(
    db: Session,
    application_id: int,
) -> Sequence[ApplicationStatusHistory]:
    get_application_or_raise(db, application_id)
    statement = (
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == application_id)
        .order_by(
            ApplicationStatusHistory.changed_at.asc(),
            ApplicationStatusHistory.id.asc(),
        )
    )
    return db.scalars(statement).all()


def _get_candidate_or_raise(db: Session, candidate_id: int) -> CandidateProfile:
    candidate = db.get(CandidateProfile, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError("Candidate not found")
    return candidate


def _get_job_or_raise(db: Session, job_id: int) -> JobPosting:
    job = db.get(JobPosting, job_id)
    if job is None:
        raise JobNotFoundError("Job not found")
    return job


def _get_application_by_candidate_job(
    db: Session,
    candidate_id: int,
    job_id: int,
) -> Application | None:
    return db.scalar(
        select(Application).where(
            Application.candidate_id == candidate_id,
            Application.job_id == job_id,
        ),
    )


def _is_duplicate_candidate_job_error(exc: IntegrityError) -> bool:
    original = exc.orig
    diagnostics = getattr(original, "diag", None)
    constraint_name = getattr(diagnostics, "constraint_name", None)
    return constraint_name == "uq_applications_candidate_job"
