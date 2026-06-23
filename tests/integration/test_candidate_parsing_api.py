from collections.abc import Generator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from backend.database.session import session_scope
from backend.main import app
from backend.models.candidate import CandidateProfile
from backend.models.candidate_parse_result import CandidateParseResult, CandidateSkill
from backend.models.job import JobPosting
from backend.models.job_parse_result import JobParseResult
from backend.models.skill import JobSkill, Skill


RESUME_TEXT = (
    "Fictional candidate resume. Built analytics workflows with Python, SQL, "
    "PostgreSQL, and Power BI. More than 5 years of experience. "
    "Bachelor's degree in information systems."
)
UPDATED_RESUME_TEXT = (
    "Fictional updated resume. Built APIs with FastAPI and Docker. "
    "Over 7 years of experience. MBA completed."
)
JOB_DESCRIPTION = (
    "Requirements: Python and SQL with 3+ years of experience. "
    "Bachelor's degree required for this fictional job."
)
TEST_NORMALIZED_SKILLS = {
    "python",
    "sql",
    "postgresql",
    "power_bi",
    "fastapi",
    "docker",
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def parse_test_context() -> Generator[dict[str, Any], None, None]:
    with session_scope() as session:
        starting_candidate_count = session.scalar(select(func.count(CandidateProfile.id)))
        starting_job_count = session.scalar(select(func.count(JobPosting.id)))
        starting_job_skill_count = session.scalar(select(func.count(JobSkill.id)))
        starting_job_parse_result_count = session.scalar(
            select(func.count(JobParseResult.id)),
        )
        existing_skill_names = set(
            session.scalars(
                select(Skill.normalized_name).where(
                    Skill.normalized_name.in_(TEST_NORMALIZED_SKILLS),
                ),
            ).all(),
        )

    context: dict[str, Any] = {
        "candidate_ids": [],
        "job_ids": [],
        "starting_candidate_count": starting_candidate_count,
        "starting_job_count": starting_job_count,
        "starting_job_skill_count": starting_job_skill_count,
        "starting_job_parse_result_count": starting_job_parse_result_count,
        "existing_skill_names": existing_skill_names,
    }

    try:
        yield context
    finally:
        candidate_ids = cast(list[int], context["candidate_ids"])
        job_ids = cast(list[int], context["job_ids"])
        with session_scope() as session:
            if candidate_ids:
                session.execute(
                    delete(CandidateProfile).where(
                        CandidateProfile.id.in_(candidate_ids),
                    ),
                )
                session.commit()
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

                job_reference_count = session.scalar(
                    select(func.count(JobSkill.id)).where(JobSkill.skill_id == skill.id),
                )
                candidate_reference_count = session.scalar(
                    select(func.count(CandidateSkill.id)).where(
                        CandidateSkill.skill_id == skill.id,
                    ),
                )
                if job_reference_count == 0 and candidate_reference_count == 0:
                    session.delete(skill)
            session.commit()

            ending_candidate_count = session.scalar(select(func.count(CandidateProfile.id)))
            ending_job_count = session.scalar(select(func.count(JobPosting.id)))
            ending_job_skill_count = session.scalar(select(func.count(JobSkill.id)))
            ending_job_parse_result_count = session.scalar(
                select(func.count(JobParseResult.id)),
            )

        assert ending_candidate_count == context["starting_candidate_count"]
        assert ending_job_count == context["starting_job_count"]
        assert ending_job_skill_count == context["starting_job_skill_count"]
        assert ending_job_parse_result_count == context["starting_job_parse_result_count"]


def create_candidate(
    client: TestClient,
    parse_test_context: dict[str, Any],
    resume_text: str | None = RESUME_TEXT,
    full_name: str = "Fictional Candidate",
) -> dict:
    response = client.post(
        "/candidates",
        json={
            "full_name": full_name,
            "headline": "Fictional Analyst",
            "location": "Toronto, ON",
            "professional_summary": "Fictional profile for parser integration tests.",
            "years_experience": 2,
            "resume_text": resume_text,
        },
    )
    assert response.status_code == 201
    candidate = response.json()
    cast(list[int], parse_test_context["candidate_ids"]).append(candidate["id"])
    return candidate


def create_and_parse_job(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> dict:
    response = client.post(
        "/jobs",
        json={
            "title": "Fictional Data Analyst",
            "company": "Northstar Labs",
            "location": "Toronto, ON",
            "employment_type": "full_time",
            "work_mode": "hybrid",
            "source_url": "https://example.com/jobs/fictional-data-analyst",
            "description": JOB_DESCRIPTION,
        },
    )
    assert response.status_code == 201
    job = response.json()
    cast(list[int], parse_test_context["job_ids"]).append(job["id"])
    assert client.post(f"/jobs/{job['id']}/parse").status_code == 200
    return job


@pytest.mark.integration
def test_parse_candidate_and_retrieve_saved_result(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> None:
    candidate = create_candidate(client, parse_test_context)

    parse_response = client.post(f"/candidates/{candidate['id']}/parse")
    retrieve_response = client.get(f"/candidates/{candidate['id']}/parse-result")

    assert parse_response.status_code == 200
    assert retrieve_response.status_code == 200
    assert parse_response.json() == retrieve_response.json()
    result = parse_response.json()
    assert result["candidate_id"] == candidate["id"]
    assert result["parser_version"] == "candidate-deterministic-v1"
    assert result["parsed_years_experience"] == 5
    assert result["education_level"] == "bachelor"
    assert "resume_text" not in result
    assert [skill["normalized_name"] for skill in result["skills"]] == [
        "postgresql",
        "power_bi",
        "python",
        "sql",
    ]


@pytest.mark.integration
def test_parsing_does_not_modify_candidate_profile_fields(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> None:
    candidate = create_candidate(client, parse_test_context)
    before = client.get(f"/candidates/{candidate['id']}").json()

    parse_response = client.post(f"/candidates/{candidate['id']}/parse")
    after = client.get(f"/candidates/{candidate['id']}").json()

    assert parse_response.status_code == 200
    for field_name in (
        "full_name",
        "headline",
        "location",
        "professional_summary",
        "years_experience",
        "resume_text",
        "updated_at",
    ):
        assert after[field_name] == before[field_name]


@pytest.mark.integration
def test_repeated_parsing_reuses_skills_and_creates_no_duplicates(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> None:
    candidate = create_candidate(client, parse_test_context)
    first_response = client.post(f"/candidates/{candidate['id']}/parse")
    second_response = client.post(f"/candidates/{candidate['id']}/parse")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["skills"] == second_response.json()["skills"]

    with session_scope() as session:
        parse_result_count = session.scalar(
            select(func.count(CandidateParseResult.id)).where(
                CandidateParseResult.candidate_id == candidate["id"],
            ),
        )
        candidate_skill_count = session.scalar(
            select(func.count(CandidateSkill.id)).where(
                CandidateSkill.candidate_id == candidate["id"],
            ),
        )
        normalized_skill_count = session.scalar(
            select(func.count(Skill.id)).where(
                Skill.normalized_name.in_(
                    ["postgresql", "power_bi", "python", "sql"],
                ),
            ),
        )

    assert parse_result_count == 1
    assert candidate_skill_count == 4
    assert normalized_skill_count == 4


@pytest.mark.integration
def test_changed_resume_text_replaces_only_selected_candidate_skills(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> None:
    selected = create_candidate(client, parse_test_context, full_name="Selected Candidate")
    other = create_candidate(client, parse_test_context, full_name="Other Candidate")
    assert client.post(f"/candidates/{selected['id']}/parse").status_code == 200
    other_parse = client.post(f"/candidates/{other['id']}/parse")
    assert other_parse.status_code == 200

    update_response = client.patch(
        f"/candidates/{selected['id']}",
        json={"resume_text": UPDATED_RESUME_TEXT},
    )
    assert update_response.status_code == 200

    reparsed = client.post(f"/candidates/{selected['id']}/parse")

    assert reparsed.status_code == 200
    assert [skill["normalized_name"] for skill in reparsed.json()["skills"]] == [
        "docker",
        "fastapi",
    ]
    assert reparsed.json()["parsed_years_experience"] == 7
    assert reparsed.json()["education_level"] == "master"

    other_result = client.get(f"/candidates/{other['id']}/parse-result")
    assert other_result.status_code == 200
    assert other_result.json()["skills"] == other_parse.json()["skills"]


@pytest.mark.integration
def test_missing_resume_and_unparsed_candidate_responses(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> None:
    missing_parse = client.post("/candidates/999999999/parse")
    missing_result = client.get("/candidates/999999999/parse-result")
    no_resume = create_candidate(client, parse_test_context, resume_text="   ")
    unparsed = create_candidate(client, parse_test_context)

    no_resume_parse = client.post(f"/candidates/{no_resume['id']}/parse")
    unparsed_result = client.get(f"/candidates/{unparsed['id']}/parse-result")

    assert missing_parse.status_code == 404
    assert missing_parse.json() == {"detail": "Candidate not found"}
    assert missing_result.status_code == 404
    assert missing_result.json() == {"detail": "Candidate not found"}
    assert no_resume_parse.status_code == 409
    assert no_resume_parse.json() == {"detail": "Candidate resume text is required"}
    assert unparsed_result.status_code == 404
    assert unparsed_result.json() == {"detail": "Candidate has not been parsed"}


@pytest.mark.integration
def test_candidate_delete_cascades_parse_data_and_preserves_shared_skills_and_jobs(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> None:
    job = create_and_parse_job(client, parse_test_context)
    candidate = create_candidate(client, parse_test_context)
    assert client.post(f"/candidates/{candidate['id']}/parse").status_code == 200

    with session_scope() as session:
        candidate_skill_ids = set(
            session.scalars(
                select(CandidateSkill.skill_id).where(
                    CandidateSkill.candidate_id == candidate["id"],
                ),
            ).all(),
        )
        job_skill_count_before_delete = session.scalar(
            select(func.count(JobSkill.id)).where(JobSkill.job_id == job["id"]),
        )
        job_parse_count_before_delete = session.scalar(
            select(func.count(JobParseResult.id)).where(JobParseResult.job_id == job["id"]),
        )

    delete_response = client.delete(f"/candidates/{candidate['id']}")

    assert delete_response.status_code == 204
    with session_scope() as session:
        candidate_parse_count = session.scalar(
            select(func.count(CandidateParseResult.id)).where(
                CandidateParseResult.candidate_id == candidate["id"],
            ),
        )
        candidate_skill_count = session.scalar(
            select(func.count(CandidateSkill.id)).where(
                CandidateSkill.candidate_id == candidate["id"],
            ),
        )
        remaining_skill_count = session.scalar(
            select(func.count(Skill.id)).where(Skill.id.in_(candidate_skill_ids)),
        )
        job_skill_count_after_delete = session.scalar(
            select(func.count(JobSkill.id)).where(JobSkill.job_id == job["id"]),
        )
        job_parse_count_after_delete = session.scalar(
            select(func.count(JobParseResult.id)).where(JobParseResult.job_id == job["id"]),
        )

    assert candidate_parse_count == 0
    assert candidate_skill_count == 0
    assert remaining_skill_count == len(candidate_skill_ids)
    assert job_skill_count_after_delete == job_skill_count_before_delete
    assert job_parse_count_after_delete == job_parse_count_before_delete
