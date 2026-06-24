from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from backend.database.session import session_scope
from backend.main import app
from backend.models.application import Application, ApplicationStatusHistory
from backend.models.candidate import CandidateProfile
from backend.models.candidate_parse_result import CandidateParseResult, CandidateSkill
from backend.models.job import JobPosting
from backend.models.job_parse_result import JobParseResult
from backend.models.match_result import MatchResult, MatchSkillDetail
from backend.models.skill import JobSkill, Skill


CANDIDATE_RESUME = (
    "Fictional application candidate resume. Built reports with Python, SQL, "
    "and Power BI. More than 4 years of experience. Bachelor's degree completed."
)
JOB_DESCRIPTION = (
    "Requirements: Python and SQL with 3+ years of experience. "
    "Bachelor's degree required for this fictional application tracking role. "
    "Preferred qualifications: Power BI is nice to have."
)
TEST_NORMALIZED_SKILLS = {"python", "sql", "power_bi"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def application_test_context() -> Generator[dict[str, Any], None, None]:
    with session_scope() as session:
        existing_skill_names = set(
            session.scalars(
                select(Skill.normalized_name).where(
                    Skill.normalized_name.in_(TEST_NORMALIZED_SKILLS),
                ),
            ).all(),
        )
        starting_counts = _record_counts(session)

    context: dict[str, Any] = {
        "application_ids": [],
        "candidate_ids": [],
        "job_ids": [],
        "existing_skill_names": existing_skill_names,
        "starting_counts": starting_counts,
        "ending_counts": None,
    }

    try:
        yield context
    finally:
        application_ids = cast(list[int], context["application_ids"])
        candidate_ids = cast(list[int], context["candidate_ids"])
        job_ids = cast(list[int], context["job_ids"])
        with session_scope() as session:
            if application_ids:
                session.execute(
                    delete(Application).where(Application.id.in_(application_ids)),
                )
            if candidate_ids:
                session.execute(
                    delete(CandidateProfile).where(
                        CandidateProfile.id.in_(candidate_ids),
                    ),
                )
            if job_ids:
                session.execute(delete(JobPosting).where(JobPosting.id.in_(job_ids)))
            session.commit()

            existing_skill_names = cast(set[str], context["existing_skill_names"])
            removable_skill_names = TEST_NORMALIZED_SKILLS - existing_skill_names
            for normalized_name in sorted(removable_skill_names):
                skill = session.scalar(
                    select(Skill).where(Skill.normalized_name == normalized_name),
                )
                if skill is None:
                    continue

                if _skill_reference_count(session, skill.id) == 0:
                    session.delete(skill)
            session.commit()

            ending_counts = _record_counts(session)
            context["ending_counts"] = ending_counts

        assert ending_counts == context["starting_counts"]


def _record_counts(session) -> dict[str, int]:
    return {
        "applications": session.scalar(select(func.count(Application.id))) or 0,
        "application_status_history": session.scalar(
            select(func.count(ApplicationStatusHistory.id)),
        )
        or 0,
        "candidates": session.scalar(select(func.count(CandidateProfile.id))) or 0,
        "jobs": session.scalar(select(func.count(JobPosting.id))) or 0,
        "candidate_parse_results": session.scalar(
            select(func.count(CandidateParseResult.id)),
        )
        or 0,
        "candidate_skills": session.scalar(select(func.count(CandidateSkill.id))) or 0,
        "job_parse_results": session.scalar(select(func.count(JobParseResult.id))) or 0,
        "job_skills": session.scalar(select(func.count(JobSkill.id))) or 0,
        "match_results": session.scalar(select(func.count(MatchResult.id))) or 0,
        "match_skill_details": session.scalar(select(func.count(MatchSkillDetail.id))) or 0,
    }


def _skill_reference_count(session, skill_id: int) -> int:
    candidate_references = session.scalar(
        select(func.count(CandidateSkill.id)).where(CandidateSkill.skill_id == skill_id),
    )
    job_references = session.scalar(
        select(func.count(JobSkill.id)).where(JobSkill.skill_id == skill_id),
    )
    match_references = session.scalar(
        select(func.count(MatchSkillDetail.id)).where(
            MatchSkillDetail.skill_id == skill_id,
        ),
    )
    return (candidate_references or 0) + (job_references or 0) + (match_references or 0)


def create_candidate(
    client: TestClient,
    context: dict[str, Any],
    full_name: str = "Fictional Application Candidate",
) -> dict:
    response = client.post(
        "/candidates",
        json={
            "full_name": full_name,
            "headline": "Fictional Analyst",
            "location": "Toronto, ON",
            "professional_summary": "Fictional profile for application tests.",
            "years_experience": 2,
            "resume_text": CANDIDATE_RESUME,
        },
    )
    assert response.status_code == 201
    candidate = response.json()
    cast(list[int], context["candidate_ids"]).append(candidate["id"])
    return candidate


def create_job(
    client: TestClient,
    context: dict[str, Any],
    title: str = "Fictional Application Job",
) -> dict:
    response = client.post(
        "/jobs",
        json={
            "title": title,
            "company": "Northstar Labs",
            "location": "Toronto, ON",
            "employment_type": "full_time",
            "work_mode": "hybrid",
            "source_url": "https://example.com/jobs/fictional-application-job",
            "description": JOB_DESCRIPTION,
        },
    )
    assert response.status_code == 201
    job = response.json()
    cast(list[int], context["job_ids"]).append(job["id"])
    return job


def create_candidate_and_job(
    client: TestClient,
    context: dict[str, Any],
) -> tuple[dict, dict]:
    return create_candidate(client, context), create_job(client, context)


def create_application(
    client: TestClient,
    context: dict[str, Any],
    candidate_id: int,
    job_id: int,
    status: str | None = None,
    notes: str | None = "Fictional note for application tests.",
) -> dict:
    payload: dict[str, Any] = {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "notes": notes,
    }
    if status is not None:
        payload["status"] = status

    response = client.post("/applications", json=payload)
    assert response.status_code == 201
    application = response.json()
    cast(list[int], context["application_ids"]).append(application["id"])
    return application


@pytest.mark.integration
def test_create_default_saved_and_initial_history(
    client: TestClient,
    application_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_and_job(client, application_test_context)

    application = create_application(
        client,
        application_test_context,
        candidate["id"],
        job["id"],
    )
    history_response = client.get(f"/applications/{application['id']}/status-history")

    assert application["status"] == "saved"
    assert application["candidate_id"] == candidate["id"]
    assert application["job_id"] == job["id"]
    assert history_response.status_code == 200
    assert history_response.json() == [
        {
            "id": history_response.json()[0]["id"],
            "application_id": application["id"],
            "previous_status": None,
            "new_status": "saved",
            "changed_at": history_response.json()[0]["changed_at"],
        },
    ]


@pytest.mark.integration
def test_create_with_explicit_status_and_retrieve_detail(
    client: TestClient,
    application_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_and_job(client, application_test_context)

    application = create_application(
        client,
        application_test_context,
        candidate["id"],
        job["id"],
        status="interview",
        notes="Fictional interview scheduled.",
    )
    retrieve_response = client.get(f"/applications/{application['id']}")
    history_response = client.get(f"/applications/{application['id']}/status-history")

    assert retrieve_response.status_code == 200
    detail = retrieve_response.json()
    assert detail["status"] == "interview"
    assert detail["notes"] == "Fictional interview scheduled."
    assert "resume_text" not in detail
    assert "description" not in detail
    assert [row["new_status"] for row in history_response.json()] == ["interview"]


@pytest.mark.integration
def test_list_ordering_and_summary_excludes_notes(
    client: TestClient,
    application_test_context: dict[str, Any],
) -> None:
    first_candidate, first_job = create_candidate_and_job(client, application_test_context)
    second_candidate = create_candidate(
        client,
        application_test_context,
        full_name="Second Fictional Application Candidate",
    )
    second_job = create_job(
        client,
        application_test_context,
        title="Second Fictional Application Job",
    )
    first = create_application(
        client,
        application_test_context,
        first_candidate["id"],
        first_job["id"],
    )
    second = create_application(
        client,
        application_test_context,
        second_candidate["id"],
        second_job["id"],
    )

    response = client.get("/applications")

    assert response.status_code == 200
    applications = response.json()
    created = [
        application
        for application in applications
        if application["id"] in {first["id"], second["id"]}
    ]
    assert [application["id"] for application in created] == [second["id"], first["id"]]
    for application in created:
        assert "notes" not in application


@pytest.mark.integration
def test_partial_update_clearing_and_status_history_rules(
    client: TestClient,
    application_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_and_job(client, application_test_context)
    application = create_application(
        client,
        application_test_context,
        candidate["id"],
        job["id"],
        notes="Fictional note to clear.",
    )

    update_response = client.patch(
        f"/applications/{application['id']}",
        json={"notes": None, "next_follow_up_at": "2026-02-01T10:00:00Z"},
    )
    same_status_response = client.patch(
        f"/applications/{application['id']}",
        json={"status": "saved", "notes": "Updated fictional note."},
    )
    notes_only_response = client.patch(
        f"/applications/{application['id']}",
        json={"notes": "Notes-only fictional update."},
    )
    history_response = client.get(f"/applications/{application['id']}/status-history")

    assert update_response.status_code == 200
    assert update_response.json()["notes"] is None
    assert update_response.json()["status"] == "saved"
    assert update_response.json()["candidate_id"] == application["candidate_id"]
    assert same_status_response.status_code == 200
    assert notes_only_response.status_code == 200
    assert len(history_response.json()) == 1


@pytest.mark.integration
def test_status_change_and_applied_at_behavior(
    client: TestClient,
    application_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_and_job(client, application_test_context)
    application = create_application(
        client,
        application_test_context,
        candidate["id"],
        job["id"],
    )

    applied_response = client.patch(
        f"/applications/{application['id']}",
        json={"status": "applied"},
    )
    interview_response = client.patch(
        f"/applications/{application['id']}",
        json={"status": "interview"},
    )
    history_response = client.get(f"/applications/{application['id']}/status-history")

    assert applied_response.status_code == 200
    assert applied_response.json()["status"] == "applied"
    assert applied_response.json()["applied_at"] is not None
    assert interview_response.status_code == 200
    assert interview_response.json()["applied_at"] == applied_response.json()["applied_at"]
    assert [row["new_status"] for row in history_response.json()] == [
        "saved",
        "applied",
        "interview",
    ]


@pytest.mark.integration
def test_explicit_applied_at_is_preserved(
    client: TestClient,
    application_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_and_job(client, application_test_context)
    application = create_application(
        client,
        application_test_context,
        candidate["id"],
        job["id"],
    )
    explicit_applied_at = datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc)

    response = client.patch(
        f"/applications/{application['id']}",
        json={"status": "applied", "applied_at": explicit_applied_at.isoformat()},
    )

    assert response.status_code == 200
    actual_applied_at = datetime.fromisoformat(
        response.json()["applied_at"].replace("Z", "+00:00"),
    )
    assert actual_applied_at == explicit_applied_at

    second_candidate = create_candidate(
        client,
        application_test_context,
        full_name="Second Explicit Applied At Candidate",
    )
    second_job = create_job(
        client,
        application_test_context,
        title="Second Explicit Applied At Job",
    )
    second_application = create_application(
        client,
        application_test_context,
        second_candidate["id"],
        second_job["id"],
    )

    null_response = client.patch(
        f"/applications/{second_application['id']}",
        json={"status": "applied", "applied_at": None},
    )

    assert null_response.status_code == 200
    assert null_response.json()["applied_at"] is None


@pytest.mark.integration
def test_duplicate_pair_and_database_uniqueness(
    client: TestClient,
    application_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_and_job(client, application_test_context)
    create_application(client, application_test_context, candidate["id"], job["id"])

    duplicate_response = client.post(
        "/applications",
        json={"candidate_id": candidate["id"], "job_id": job["id"]},
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "detail": "Application already exists for this candidate and job",
    }

    with session_scope() as session:
        duplicate = Application(
            candidate_id=candidate["id"],
            job_id=job["id"],
            status="saved",
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


@pytest.mark.integration
def test_missing_records_and_invalid_patch(
    client: TestClient,
    application_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_and_job(client, application_test_context)
    application = create_application(
        client,
        application_test_context,
        candidate["id"],
        job["id"],
    )

    missing_candidate = client.post(
        "/applications",
        json={"candidate_id": 999999999, "job_id": job["id"]},
    )
    missing_job = client.post(
        "/applications",
        json={"candidate_id": candidate["id"], "job_id": 999999999},
    )
    missing_application = client.get("/applications/999999999")
    empty_patch = client.patch(f"/applications/{application['id']}", json={})
    invalid_patch = client.patch(
        f"/applications/{application['id']}",
        json={"status": None, "unexpected": "field"},
    )

    assert missing_candidate.status_code == 404
    assert missing_candidate.json() == {"detail": "Candidate not found"}
    assert missing_job.status_code == 404
    assert missing_job.json() == {"detail": "Job not found"}
    assert missing_application.status_code == 404
    assert missing_application.json() == {"detail": "Application not found"}
    assert empty_patch.status_code == 422
    assert invalid_patch.status_code == 422


@pytest.mark.integration
def test_direct_application_delete_removes_history_only(
    client: TestClient,
    application_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_and_job(client, application_test_context)
    application = create_application(
        client,
        application_test_context,
        candidate["id"],
        job["id"],
    )
    assert (
        client.patch(
            f"/applications/{application['id']}",
            json={"status": "interview"},
        ).status_code
        == 200
    )
    before_counts = _owned_source_counts(candidate["id"], job["id"])

    delete_response = client.delete(f"/applications/{application['id']}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    with session_scope() as session:
        application_count = session.scalar(
            select(func.count(Application.id)).where(Application.id == application["id"]),
        )
        history_count = session.scalar(
            select(func.count(ApplicationStatusHistory.id)).where(
                ApplicationStatusHistory.application_id == application["id"],
            ),
        )
    assert application_count == 0
    assert history_count == 0
    assert _owned_source_counts(candidate["id"], job["id"]) == before_counts


@pytest.mark.integration
def test_candidate_and_job_delete_cascade_application_history(
    client: TestClient,
    application_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_and_job(client, application_test_context)
    application = create_application(
        client,
        application_test_context,
        candidate["id"],
        job["id"],
    )

    candidate_delete = client.delete(f"/candidates/{candidate['id']}")

    assert candidate_delete.status_code == 204
    _assert_application_and_history_removed(application["id"])

    second_candidate, second_job = create_candidate_and_job(
        client,
        application_test_context,
    )
    second_application = create_application(
        client,
        application_test_context,
        second_candidate["id"],
        second_job["id"],
    )

    job_delete = client.delete(f"/jobs/{second_job['id']}")

    assert job_delete.status_code == 204
    _assert_application_and_history_removed(second_application["id"])


@pytest.mark.integration
def test_ordinary_operations_preserve_parse_match_and_shared_skill_rows(
    client: TestClient,
    application_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_and_job(client, application_test_context)
    assert client.post(f"/candidates/{candidate['id']}/parse").status_code == 200
    assert client.post(f"/jobs/{job['id']}/parse").status_code == 200
    assert client.post(f"/candidates/{candidate['id']}/jobs/{job['id']}/match").status_code == 200
    before_counts = _owned_source_counts(candidate["id"], job["id"])

    application = create_application(
        client,
        application_test_context,
        candidate["id"],
        job["id"],
    )
    assert (
        client.patch(
            f"/applications/{application['id']}",
            json={"status": "applied", "notes": "Fictional submitted note."},
        ).status_code
        == 200
    )
    assert client.get(f"/applications/{application['id']}").status_code == 200

    assert _owned_source_counts(candidate["id"], job["id"]) == before_counts


def _owned_source_counts(candidate_id: int, job_id: int) -> dict[str, int]:
    with session_scope() as session:
        return {
            "candidate": session.scalar(
                select(func.count(CandidateProfile.id)).where(
                    CandidateProfile.id == candidate_id,
                ),
            )
            or 0,
            "job": session.scalar(
                select(func.count(JobPosting.id)).where(JobPosting.id == job_id),
            )
            or 0,
            "candidate_parse_results": session.scalar(
                select(func.count(CandidateParseResult.id)).where(
                    CandidateParseResult.candidate_id == candidate_id,
                ),
            )
            or 0,
            "candidate_skills": session.scalar(
                select(func.count(CandidateSkill.id)).where(
                    CandidateSkill.candidate_id == candidate_id,
                ),
            )
            or 0,
            "job_parse_results": session.scalar(
                select(func.count(JobParseResult.id)).where(JobParseResult.job_id == job_id),
            )
            or 0,
            "job_skills": session.scalar(
                select(func.count(JobSkill.id)).where(JobSkill.job_id == job_id),
            )
            or 0,
            "match_results": session.scalar(
                select(func.count(MatchResult.id)).where(
                    MatchResult.candidate_id == candidate_id,
                    MatchResult.job_id == job_id,
                ),
            )
            or 0,
            "match_skill_details": session.scalar(
                select(func.count(MatchSkillDetail.id))
                .join(MatchResult)
                .where(
                    MatchResult.candidate_id == candidate_id,
                    MatchResult.job_id == job_id,
                ),
            )
            or 0,
            "shared_skills": session.scalar(
                select(func.count(Skill.id)).where(
                    Skill.normalized_name.in_(TEST_NORMALIZED_SKILLS),
                ),
            )
            or 0,
        }


def _assert_application_and_history_removed(application_id: int) -> None:
    with session_scope() as session:
        application_count = session.scalar(
            select(func.count(Application.id)).where(Application.id == application_id),
        )
        history_count = session.scalar(
            select(func.count(ApplicationStatusHistory.id)).where(
                ApplicationStatusHistory.application_id == application_id,
            ),
        )

    assert application_count == 0
    assert history_count == 0
