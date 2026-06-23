from collections.abc import Generator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from backend.database.session import session_scope
from backend.main import app
from backend.models.candidate import CandidateProfile
from backend.models.job import JobPosting
from backend.models.job_parse_result import JobParseResult
from backend.models.skill import JobSkill, Skill


PARSE_DESCRIPTION = (
    "Requirements: Python, SQL, PostgreSQL, and 3+ years of experience. "
    "Bachelor's degree required for this fictional local analytics role. "
    "Preferred qualifications: Power BI and Tableau are nice to have."
)
UPDATED_DESCRIPTION = (
    "Requirements: FastAPI, Docker, and minimum of 5 years of experience. "
    "College diploma required for this fictional backend platform role. "
    "Preferred: AWS is considered an asset."
)
UNRELATED_DESCRIPTION = (
    "This fictional unrelated job uses Excel for documentation and avoids parser "
    "checks so cleanup can verify unrelated jobs remain untouched."
)
TEST_NORMALIZED_SKILLS = {
    "python",
    "sql",
    "postgresql",
    "power_bi",
    "tableau",
    "fastapi",
    "docker",
    "aws",
    "excel",
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def parse_test_context() -> Generator[dict[str, Any], None, None]:
    with session_scope() as session:
        starting_candidate_count = session.scalar(select(func.count(CandidateProfile.id)))
        starting_job_count = session.scalar(select(func.count(JobPosting.id)))
        existing_skill_names = set(
            session.scalars(
                select(Skill.normalized_name).where(
                    Skill.normalized_name.in_(TEST_NORMALIZED_SKILLS),
                ),
            ).all(),
        )

    context: dict[str, Any] = {
        "job_ids": [],
        "starting_candidate_count": starting_candidate_count,
        "starting_job_count": starting_job_count,
        "existing_skill_names": existing_skill_names,
    }

    try:
        yield context
    finally:
        job_ids = cast(list[int], context["job_ids"])
        with session_scope() as session:
            if job_ids:
                session.execute(
                    delete(JobPosting).where(JobPosting.id.in_(job_ids)),
                )
                session.commit()

            existing_skill_names = cast(set[str], context["existing_skill_names"])
            removable_skill_names = TEST_NORMALIZED_SKILLS - existing_skill_names
            for normalized_name in sorted(removable_skill_names):
                skill = session.scalar(
                    select(Skill).where(Skill.normalized_name == normalized_name),
                )
                if skill is None:
                    continue

                reference_count = session.scalar(
                    select(func.count(JobSkill.id)).where(JobSkill.skill_id == skill.id),
                )
                if reference_count == 0:
                    session.delete(skill)
            session.commit()

            ending_candidate_count = session.scalar(select(func.count(CandidateProfile.id)))
            ending_job_count = session.scalar(select(func.count(JobPosting.id)))

        assert ending_candidate_count == context["starting_candidate_count"]
        assert ending_job_count == context["starting_job_count"]


def create_job(
    client: TestClient,
    parse_test_context: dict[str, Any],
    description: str = PARSE_DESCRIPTION,
    title: str = "Analytics Engineer",
) -> dict:
    response = client.post(
        "/jobs",
        json={
            "title": title,
            "company": "Northstar Labs",
            "location": "Toronto, ON",
            "employment_type": "full_time",
            "work_mode": "hybrid",
            "source_url": "https://example.com/jobs/analytics-engineer",
            "description": description,
        },
    )
    assert response.status_code == 201
    job = response.json()
    cast(list[int], parse_test_context["job_ids"]).append(job["id"])
    return job


@pytest.mark.integration
def test_parse_existing_job_and_retrieve_result(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> None:
    job = create_job(client, parse_test_context)

    parse_response = client.post(f"/jobs/{job['id']}/parse")
    retrieve_response = client.get(f"/jobs/{job['id']}/parse-result")

    assert parse_response.status_code == 200
    assert retrieve_response.status_code == 200
    assert parse_response.json() == retrieve_response.json()
    result = parse_response.json()
    assert result["job_id"] == job["id"]
    assert result["parser_version"] == "deterministic-v1"
    assert result["minimum_years_experience"] == 3
    assert result["education_requirement"] == "bachelor"
    assert [skill["normalized_name"] for skill in result["required_skills"]] == [
        "postgresql",
        "python",
        "sql",
    ]
    assert [skill["normalized_name"] for skill in result["preferred_skills"]] == [
        "power_bi",
        "tableau",
    ]


@pytest.mark.integration
def test_repeated_parsing_reuses_skills_and_creates_no_duplicates(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> None:
    job = create_job(client, parse_test_context)

    first_response = client.post(f"/jobs/{job['id']}/parse")
    second_response = client.post(f"/jobs/{job['id']}/parse")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["required_skills"] == second_response.json()["required_skills"]
    assert first_response.json()["preferred_skills"] == second_response.json()["preferred_skills"]

    with session_scope() as session:
        parse_result_count = session.scalar(
            select(func.count(JobParseResult.id)).where(JobParseResult.job_id == job["id"]),
        )
        job_skill_count = session.scalar(
            select(func.count(JobSkill.id)).where(JobSkill.job_id == job["id"]),
        )
        normalized_skill_count = session.scalar(
            select(func.count(Skill.id)).where(
                Skill.normalized_name.in_(
                    ["postgresql", "python", "sql", "power_bi", "tableau"],
                ),
            ),
        )

    assert parse_result_count == 1
    assert job_skill_count == 5
    assert normalized_skill_count == 5


@pytest.mark.integration
def test_reparse_replaces_only_selected_job_associations(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> None:
    selected_job = create_job(client, parse_test_context, title="Selected Analyst")
    other_job = create_job(client, parse_test_context, title="Other Analyst")

    assert client.post(f"/jobs/{selected_job['id']}/parse").status_code == 200
    other_parse = client.post(f"/jobs/{other_job['id']}/parse")
    assert other_parse.status_code == 200

    update_response = client.patch(
        f"/jobs/{selected_job['id']}",
        json={"description": UPDATED_DESCRIPTION},
    )
    assert update_response.status_code == 200

    reparsed = client.post(f"/jobs/{selected_job['id']}/parse")

    assert reparsed.status_code == 200
    assert [skill["normalized_name"] for skill in reparsed.json()["required_skills"]] == [
        "docker",
        "fastapi",
    ]
    assert [skill["normalized_name"] for skill in reparsed.json()["preferred_skills"]] == [
        "aws",
    ]

    other_result = client.get(f"/jobs/{other_job['id']}/parse-result")
    assert other_result.status_code == 200
    assert other_result.json()["required_skills"] == other_parse.json()["required_skills"]
    assert other_result.json()["preferred_skills"] == other_parse.json()["preferred_skills"]


@pytest.mark.integration
def test_missing_and_unparsed_job_responses(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> None:
    missing_parse = client.post("/jobs/999999999/parse")
    missing_result = client.get("/jobs/999999999/parse-result")
    unparsed_job = create_job(client, parse_test_context)
    unparsed_result = client.get(f"/jobs/{unparsed_job['id']}/parse-result")

    assert missing_parse.status_code == 404
    assert missing_parse.json() == {"detail": "Job not found"}
    assert missing_result.status_code == 404
    assert missing_result.json() == {"detail": "Job not found"}
    assert unparsed_result.status_code == 404
    assert unparsed_result.json() == {"detail": "Job has not been parsed"}


@pytest.mark.integration
def test_deleting_job_cascades_parse_data_but_preserves_skills(
    client: TestClient,
    parse_test_context: dict[str, Any],
) -> None:
    job = create_job(client, parse_test_context)
    assert client.post(f"/jobs/{job['id']}/parse").status_code == 200

    with session_scope() as session:
        skill_ids = set(
            session.scalars(
                select(JobSkill.skill_id).where(JobSkill.job_id == job["id"]),
            ).all(),
        )

    delete_response = client.delete(f"/jobs/{job['id']}")

    assert delete_response.status_code == 204
    with session_scope() as session:
        parse_result_count = session.scalar(
            select(func.count(JobParseResult.id)).where(JobParseResult.job_id == job["id"]),
        )
        job_skill_count = session.scalar(
            select(func.count(JobSkill.id)).where(JobSkill.job_id == job["id"]),
        )
        remaining_skill_count = session.scalar(
            select(func.count(Skill.id)).where(Skill.id.in_(skill_ids)),
        )

    assert parse_result_count == 0
    assert job_skill_count == 0
    assert remaining_skill_count == len(skill_ids)
