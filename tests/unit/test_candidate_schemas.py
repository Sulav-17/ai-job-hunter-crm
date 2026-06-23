import pytest
from pydantic import ValidationError

from backend.schemas.candidate import CandidateCreate, CandidateUpdate


def test_candidate_create_accepts_valid_payload() -> None:
    candidate = CandidateCreate(
        full_name="  Avery Stone  ",
        headline="  Data analyst  ",
        location="  Toronto, ON  ",
        professional_summary="Builds practical reporting workflows.",
        years_experience=4,
        resume_text="Fictional resume text for testing only.",
    )

    assert candidate.full_name == "Avery Stone"
    assert candidate.headline == "Data analyst"
    assert candidate.location == "Toronto, ON"
    assert candidate.years_experience == 4


def test_candidate_create_rejects_negative_years_experience() -> None:
    with pytest.raises(ValidationError):
        CandidateCreate(full_name="Avery Stone", years_experience=-1)


def test_candidate_create_rejects_years_experience_above_80() -> None:
    with pytest.raises(ValidationError):
        CandidateCreate(full_name="Avery Stone", years_experience=81)


def test_candidate_update_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError):
        CandidateUpdate()


def test_candidate_create_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        CandidateCreate(full_name="Avery Stone", favorite_color="blue")


def test_candidate_create_rejects_blank_full_name_after_trimming() -> None:
    with pytest.raises(ValidationError):
        CandidateCreate(full_name="   ")


def test_candidate_update_allows_explicit_null_for_nullable_field() -> None:
    candidate = CandidateUpdate(headline=None)

    assert candidate.model_dump(exclude_unset=True) == {"headline": None}
