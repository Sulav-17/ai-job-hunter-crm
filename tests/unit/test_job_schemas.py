import pytest
from pydantic import ValidationError

from backend.schemas.job import JobCreate, JobUpdate


VALID_DESCRIPTION = (
    "This fictional role supports internal reporting workflows, stakeholder "
    "communication, and careful documentation for a local test scenario."
)


def test_job_create_accepts_valid_payload() -> None:
    job = JobCreate(
        title="  Data Analyst  ",
        company="  Northstar Labs  ",
        location="  Toronto, ON  ",
        employment_type="full_time",
        work_mode="hybrid",
        source_url="  https://example.com/jobs/data-analyst  ",
        description=f"  {VALID_DESCRIPTION}  ",
    )

    assert job.title == "Data Analyst"
    assert job.company == "Northstar Labs"
    assert job.location == "Toronto, ON"
    assert job.source_url == "https://example.com/jobs/data-analyst"
    assert job.description == VALID_DESCRIPTION


def test_job_create_rejects_missing_required_values() -> None:
    with pytest.raises(ValidationError):
        JobCreate(description=VALID_DESCRIPTION)


def test_job_create_rejects_blank_title() -> None:
    with pytest.raises(ValidationError):
        JobCreate(title="   ", company="Northstar Labs", description=VALID_DESCRIPTION)


def test_job_create_rejects_blank_company() -> None:
    with pytest.raises(ValidationError):
        JobCreate(title="Data Analyst", company="   ", description=VALID_DESCRIPTION)


def test_job_create_rejects_short_description() -> None:
    with pytest.raises(ValidationError):
        JobCreate(title="Data Analyst", company="Northstar Labs", description="Too short")


def test_job_create_rejects_long_description() -> None:
    with pytest.raises(ValidationError):
        JobCreate(
            title="Data Analyst",
            company="Northstar Labs",
            description="x" * 50001,
        )


def test_job_create_rejects_invalid_employment_type() -> None:
    with pytest.raises(ValidationError):
        JobCreate(
            title="Data Analyst",
            company="Northstar Labs",
            employment_type="permanent",
            description=VALID_DESCRIPTION,
        )


def test_job_create_rejects_invalid_work_mode() -> None:
    with pytest.raises(ValidationError):
        JobCreate(
            title="Data Analyst",
            company="Northstar Labs",
            work_mode="office",
            description=VALID_DESCRIPTION,
        )


def test_job_create_rejects_invalid_url_scheme() -> None:
    with pytest.raises(ValidationError):
        JobCreate(
            title="Data Analyst",
            company="Northstar Labs",
            source_url="ftp://example.com/jobs/data-analyst",
            description=VALID_DESCRIPTION,
        )


def test_job_create_rejects_url_without_hostname() -> None:
    with pytest.raises(ValidationError):
        JobCreate(
            title="Data Analyst",
            company="Northstar Labs",
            source_url="https:///jobs/data-analyst",
            description=VALID_DESCRIPTION,
        )


def test_job_update_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError):
        JobUpdate()


def test_job_update_accepts_explicit_nullable_update() -> None:
    job = JobUpdate(location=None, source_url="   ")

    assert job.model_dump(exclude_unset=True) == {
        "location": None,
        "source_url": None,
    }


def test_job_create_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        JobCreate(
            title="Data Analyst",
            company="Northstar Labs",
            description=VALID_DESCRIPTION,
            salary="100000",
        )


def test_job_create_rejects_blank_enum_values() -> None:
    with pytest.raises(ValidationError):
        JobCreate(
            title="Data Analyst",
            company="Northstar Labs",
            employment_type="   ",
            description=VALID_DESCRIPTION,
        )

    with pytest.raises(ValidationError):
        JobCreate(
            title="Data Analyst",
            company="Northstar Labs",
            work_mode="",
            description=VALID_DESCRIPTION,
        )


def test_job_update_rejects_null_required_fields() -> None:
    with pytest.raises(ValidationError):
        JobUpdate(title=None)

    with pytest.raises(ValidationError):
        JobUpdate(company=None)

    with pytest.raises(ValidationError):
        JobUpdate(description=None)
