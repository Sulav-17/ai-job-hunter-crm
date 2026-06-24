from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.schemas.application import ApplicationCreate, ApplicationUpdate


def test_application_create_accepts_valid_payload() -> None:
    payload = ApplicationCreate(
        candidate_id=1,
        job_id=2,
        status="interview",
        applied_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        next_follow_up_at=datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),
        notes="Fictional application note.",
    )

    assert payload.candidate_id == 1
    assert payload.job_id == 2
    assert payload.status == "interview"
    assert payload.notes == "Fictional application note."


def test_application_create_defaults_to_saved_status() -> None:
    payload = ApplicationCreate(candidate_id=1, job_id=2)

    assert payload.status == "saved"


def test_application_create_accepts_explicit_valid_status() -> None:
    payload = ApplicationCreate(candidate_id=1, job_id=2, status="offer")

    assert payload.status == "offer"


def test_application_create_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        ApplicationCreate(candidate_id=1, job_id=2, status="custom")


def test_application_create_requires_positive_candidate_and_job_ids() -> None:
    with pytest.raises(ValidationError):
        ApplicationCreate(candidate_id=0, job_id=2)

    with pytest.raises(ValidationError):
        ApplicationCreate(candidate_id=1, job_id=-1)


def test_application_notes_maximum_length() -> None:
    payload = ApplicationCreate(candidate_id=1, job_id=2, notes="a" * 5000)
    assert payload.notes == "a" * 5000

    with pytest.raises(ValidationError):
        ApplicationCreate(candidate_id=1, job_id=2, notes="a" * 5001)


def test_application_update_accepts_valid_partial_update() -> None:
    payload = ApplicationUpdate(status="applied", notes="Submitted application.")

    assert payload.model_dump(exclude_unset=True) == {
        "notes": "Submitted application.",
        "status": "applied",
    }


def test_application_update_rejects_empty_patch() -> None:
    with pytest.raises(ValidationError):
        ApplicationUpdate()


def test_application_update_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        ApplicationUpdate(priority="high")


def test_application_update_allows_explicit_nullable_clearing() -> None:
    payload = ApplicationUpdate(
        applied_at=None,
        next_follow_up_at=None,
        notes=None,
    )

    assert payload.model_dump(exclude_unset=True) == {
        "applied_at": None,
        "next_follow_up_at": None,
        "notes": None,
    }


def test_application_update_rejects_null_status() -> None:
    with pytest.raises(ValidationError):
        ApplicationUpdate(status=None)
