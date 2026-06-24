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
from backend.models.match_result import MatchResult, MatchSkillDetail
from backend.models.skill import JobSkill, Skill


CANDIDATE_RESUME = (
    "Fictional candidate resume. Built dashboards with Python, SQL, PostgreSQL, "
    "and Power BI. More than 5 years of experience. Bachelor's degree in "
    "information systems."
)
UPDATED_CANDIDATE_RESUME = (
    "Fictional updated resume. Built services with Docker and FastAPI. "
    "More than 2 years of experience. College diploma completed."
)
JOB_DESCRIPTION = (
    "Requirements: Python, SQL, and Docker with 3+ years of experience. "
    "Bachelor's degree required for this fictional analytics job. "
    "Preferred qualifications: Power BI and Tableau are nice to have."
)
UPDATED_JOB_DESCRIPTION = (
    "Requirements: FastAPI and Docker with 2+ years of experience. "
    "College diploma required for this fictional platform job. "
    "Preferred qualifications: AWS is considered an asset."
)
UNRELATED_RESUME = (
    "Fictional unrelated resume. Used Excel for reporting. "
    "More than 1 years of experience. High school diploma completed."
)
UNRELATED_JOB_DESCRIPTION = (
    "Requirements: Excel with 1+ years of experience. "
    "High school diploma required for this fictional unrelated role."
)
TEST_NORMALIZED_SKILLS = {
    "python",
    "sql",
    "postgresql",
    "power_bi",
    "docker",
    "tableau",
    "fastapi",
    "aws",
    "excel",
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def match_test_context() -> Generator[dict[str, Any], None, None]:
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
        "candidate_ids": [],
        "job_ids": [],
        "existing_skill_names": existing_skill_names,
        "starting_counts": starting_counts,
        "ending_counts": None,
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

                reference_count = _skill_reference_count(session, skill.id)
                if reference_count == 0:
                    session.delete(skill)
            session.commit()

            ending_counts = _record_counts(session)
            context["ending_counts"] = ending_counts

        assert ending_counts == context["starting_counts"]


def _record_counts(session) -> dict[str, int]:
    return {
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
    resume_text: str = CANDIDATE_RESUME,
    full_name: str = "Fictional Match Candidate",
) -> dict:
    response = client.post(
        "/candidates",
        json={
            "full_name": full_name,
            "headline": "Fictional Analyst",
            "location": "Toronto, ON",
            "professional_summary": "Fictional profile for matching tests.",
            "years_experience": 1,
            "resume_text": resume_text,
        },
    )
    assert response.status_code == 201
    candidate = response.json()
    cast(list[int], context["candidate_ids"]).append(candidate["id"])
    return candidate


def create_job(
    client: TestClient,
    context: dict[str, Any],
    description: str = JOB_DESCRIPTION,
    title: str = "Fictional Match Job",
) -> dict:
    response = client.post(
        "/jobs",
        json={
            "title": title,
            "company": "Northstar Labs",
            "location": "Toronto, ON",
            "employment_type": "full_time",
            "work_mode": "hybrid",
            "source_url": "https://example.com/jobs/fictional-match-job",
            "description": description,
        },
    )
    assert response.status_code == 201
    job = response.json()
    cast(list[int], context["job_ids"]).append(job["id"])
    return job


def create_parsed_candidate(
    client: TestClient,
    context: dict[str, Any],
    resume_text: str = CANDIDATE_RESUME,
    full_name: str = "Fictional Match Candidate",
) -> dict:
    candidate = create_candidate(client, context, resume_text, full_name)
    assert client.post(f"/candidates/{candidate['id']}/parse").status_code == 200
    return candidate


def create_parsed_job(
    client: TestClient,
    context: dict[str, Any],
    description: str = JOB_DESCRIPTION,
    title: str = "Fictional Match Job",
) -> dict:
    job = create_job(client, context, description, title)
    assert client.post(f"/jobs/{job['id']}/parse").status_code == 200
    return job


def calculate_match(client: TestClient, candidate_id: int, job_id: int) -> dict:
    response = client.post(f"/candidates/{candidate_id}/jobs/{job_id}/match")
    assert response.status_code == 200
    return response.json()


@pytest.mark.integration
def test_calculate_and_retrieve_match(
    client: TestClient,
    match_test_context: dict[str, Any],
) -> None:
    candidate = create_parsed_candidate(client, match_test_context)
    job = create_parsed_job(client, match_test_context)

    calculated = calculate_match(client, candidate["id"], job["id"])
    retrieved_response = client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/match-result",
    )

    assert retrieved_response.status_code == 200
    assert retrieved_response.json() == calculated
    assert calculated["candidate_id"] == candidate["id"]
    assert calculated["job_id"] == job["id"]
    assert calculated["required_skill_score"] == 67
    assert calculated["preferred_skill_score"] == 50
    assert calculated["experience_score"] == 100
    assert calculated["education_score"] == 100
    assert calculated["overall_score"] == 74
    assert calculated["applicable_weights"] == {
        "required_skills": 55,
        "preferred_skills": 15,
        "experience": 20,
        "education": 10,
    }
    assert "resume_text" not in calculated
    assert "description" not in calculated


@pytest.mark.integration
def test_match_skill_lists_are_correct_and_ordered(
    client: TestClient,
    match_test_context: dict[str, Any],
) -> None:
    candidate = create_parsed_candidate(client, match_test_context)
    job = create_parsed_job(client, match_test_context)

    result = calculate_match(client, candidate["id"], job["id"])

    assert [
        skill["normalized_name"] for skill in result["matched_required_skills"]
    ] == ["python", "sql"]
    assert [
        skill["normalized_name"] for skill in result["missing_required_skills"]
    ] == ["docker"]
    assert [
        skill["normalized_name"] for skill in result["matched_preferred_skills"]
    ] == ["power_bi"]
    assert [
        skill["normalized_name"] for skill in result["missing_preferred_skills"]
    ] == ["tableau"]


@pytest.mark.integration
def test_repeated_calculation_creates_no_duplicate_rows(
    client: TestClient,
    match_test_context: dict[str, Any],
) -> None:
    candidate = create_parsed_candidate(client, match_test_context)
    job = create_parsed_job(client, match_test_context)

    first = calculate_match(client, candidate["id"], job["id"])
    second = calculate_match(client, candidate["id"], job["id"])

    assert first["overall_score"] == second["overall_score"]
    with session_scope() as session:
        match_result_count = session.scalar(
            select(func.count(MatchResult.id)).where(
                MatchResult.candidate_id == candidate["id"],
                MatchResult.job_id == job["id"],
            ),
        )
        match_result = session.scalar(
            select(MatchResult).where(
                MatchResult.candidate_id == candidate["id"],
                MatchResult.job_id == job["id"],
            ),
        )
        assert match_result is not None
        detail_count = session.scalar(
            select(func.count(MatchSkillDetail.id)).where(
                MatchSkillDetail.match_result_id == match_result.id,
            ),
        )

    assert match_result_count == 1
    assert detail_count == 5


@pytest.mark.integration
def test_candidate_parse_change_updates_score_only_after_recalculation(
    client: TestClient,
    match_test_context: dict[str, Any],
) -> None:
    candidate = create_parsed_candidate(client, match_test_context)
    job = create_parsed_job(client, match_test_context)
    original = calculate_match(client, candidate["id"], job["id"])

    update_response = client.patch(
        f"/candidates/{candidate['id']}",
        json={"resume_text": UPDATED_CANDIDATE_RESUME},
    )
    assert update_response.status_code == 200
    assert client.post(f"/candidates/{candidate['id']}/parse").status_code == 200

    stale = client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/match-result",
    ).json()
    recalculated = calculate_match(client, candidate["id"], job["id"])

    assert stale["overall_score"] == original["overall_score"]
    assert recalculated["overall_score"] != original["overall_score"]
    assert recalculated["required_skill_score"] == 33
    assert recalculated["candidate_years_used"] == 2


@pytest.mark.integration
def test_job_parse_change_updates_score_after_recalculation(
    client: TestClient,
    match_test_context: dict[str, Any],
) -> None:
    candidate = create_parsed_candidate(client, match_test_context)
    job = create_parsed_job(client, match_test_context)
    original = calculate_match(client, candidate["id"], job["id"])

    update_response = client.patch(
        f"/jobs/{job['id']}",
        json={"description": UPDATED_JOB_DESCRIPTION},
    )
    assert update_response.status_code == 200
    assert client.post(f"/jobs/{job['id']}/parse").status_code == 200

    recalculated = calculate_match(client, candidate["id"], job["id"])

    assert recalculated["overall_score"] != original["overall_score"]
    assert recalculated["required_skill_score"] == 0
    assert recalculated["preferred_skill_score"] == 0
    assert recalculated["experience_score"] == 100
    assert recalculated["education_score"] == 100


@pytest.mark.integration
def test_missing_and_unparsed_records_return_expected_errors(
    client: TestClient,
    match_test_context: dict[str, Any],
) -> None:
    parsed_candidate = create_parsed_candidate(client, match_test_context)
    parsed_job = create_parsed_job(client, match_test_context)
    unparsed_candidate = create_candidate(
        client,
        match_test_context,
        full_name="Unparsed Fictional Candidate",
    )
    unparsed_job = create_job(
        client,
        match_test_context,
        title="Unparsed Fictional Job",
    )

    missing_candidate = client.post(f"/candidates/999999999/jobs/{parsed_job['id']}/match")
    missing_job = client.post(
        f"/candidates/{parsed_candidate['id']}/jobs/999999999/match",
    )
    unparsed_candidate_response = client.post(
        f"/candidates/{unparsed_candidate['id']}/jobs/{parsed_job['id']}/match",
    )
    unparsed_job_response = client.post(
        f"/candidates/{parsed_candidate['id']}/jobs/{unparsed_job['id']}/match",
    )
    missing_match = client.get(
        f"/candidates/{parsed_candidate['id']}/jobs/{parsed_job['id']}/match-result",
    )

    assert missing_candidate.status_code == 404
    assert missing_candidate.json() == {"detail": "Candidate not found"}
    assert missing_job.status_code == 404
    assert missing_job.json() == {"detail": "Job not found"}
    assert unparsed_candidate_response.status_code == 409
    assert unparsed_candidate_response.json() == {
        "detail": "Candidate must be parsed before matching",
    }
    assert unparsed_job_response.status_code == 409
    assert unparsed_job_response.json() == {
        "detail": "Job must be parsed before matching",
    }
    assert missing_match.status_code == 404
    assert missing_match.json() == {"detail": "Match result not found"}


@pytest.mark.integration
def test_candidate_delete_cascades_only_match_owned_rows(
    client: TestClient,
    match_test_context: dict[str, Any],
) -> None:
    candidate = create_parsed_candidate(client, match_test_context)
    job = create_parsed_job(client, match_test_context)
    calculate_match(client, candidate["id"], job["id"])

    with session_scope() as session:
        skill_ids = set(
            session.scalars(
                select(MatchSkillDetail.skill_id)
                .join(MatchResult)
                .where(MatchResult.candidate_id == candidate["id"]),
            ).all(),
        )
        job_parse_count_before = session.scalar(
            select(func.count(JobParseResult.id)).where(
                JobParseResult.job_id == job["id"],
            ),
        )
        job_skill_count_before = session.scalar(
            select(func.count(JobSkill.id)).where(JobSkill.job_id == job["id"]),
        )

    delete_response = client.delete(f"/candidates/{candidate['id']}")

    assert delete_response.status_code == 204
    with session_scope() as session:
        match_count = session.scalar(
            select(func.count(MatchResult.id)).where(
                MatchResult.candidate_id == candidate["id"],
            ),
        )
        detail_count = session.scalar(
            select(func.count(MatchSkillDetail.id))
            .join(MatchResult)
            .where(MatchResult.candidate_id == candidate["id"]),
        )
        remaining_skill_count = session.scalar(
            select(func.count(Skill.id)).where(Skill.id.in_(skill_ids)),
        )
        job_parse_count_after = session.scalar(
            select(func.count(JobParseResult.id)).where(
                JobParseResult.job_id == job["id"],
            ),
        )
        job_skill_count_after = session.scalar(
            select(func.count(JobSkill.id)).where(JobSkill.job_id == job["id"]),
        )

    assert match_count == 0
    assert detail_count == 0
    assert remaining_skill_count == len(skill_ids)
    assert job_parse_count_after == job_parse_count_before
    assert job_skill_count_after == job_skill_count_before


@pytest.mark.integration
def test_job_delete_cascades_only_match_owned_rows(
    client: TestClient,
    match_test_context: dict[str, Any],
) -> None:
    candidate = create_parsed_candidate(client, match_test_context)
    job = create_parsed_job(client, match_test_context)
    calculate_match(client, candidate["id"], job["id"])

    with session_scope() as session:
        skill_ids = set(
            session.scalars(
                select(MatchSkillDetail.skill_id)
                .join(MatchResult)
                .where(MatchResult.job_id == job["id"]),
            ).all(),
        )
        candidate_parse_count_before = session.scalar(
            select(func.count(CandidateParseResult.id)).where(
                CandidateParseResult.candidate_id == candidate["id"],
            ),
        )
        candidate_skill_count_before = session.scalar(
            select(func.count(CandidateSkill.id)).where(
                CandidateSkill.candidate_id == candidate["id"],
            ),
        )

    delete_response = client.delete(f"/jobs/{job['id']}")

    assert delete_response.status_code == 204
    with session_scope() as session:
        match_count = session.scalar(
            select(func.count(MatchResult.id)).where(MatchResult.job_id == job["id"]),
        )
        detail_count = session.scalar(
            select(func.count(MatchSkillDetail.id))
            .join(MatchResult)
            .where(MatchResult.job_id == job["id"]),
        )
        remaining_skill_count = session.scalar(
            select(func.count(Skill.id)).where(Skill.id.in_(skill_ids)),
        )
        candidate_parse_count_after = session.scalar(
            select(func.count(CandidateParseResult.id)).where(
                CandidateParseResult.candidate_id == candidate["id"],
            ),
        )
        candidate_skill_count_after = session.scalar(
            select(func.count(CandidateSkill.id)).where(
                CandidateSkill.candidate_id == candidate["id"],
            ),
        )

    assert match_count == 0
    assert detail_count == 0
    assert remaining_skill_count == len(skill_ids)
    assert candidate_parse_count_after == candidate_parse_count_before
    assert candidate_skill_count_after == candidate_skill_count_before


@pytest.mark.integration
def test_matching_preserves_source_and_unrelated_records(
    client: TestClient,
    match_test_context: dict[str, Any],
) -> None:
    selected_candidate = create_parsed_candidate(client, match_test_context)
    selected_job = create_parsed_job(client, match_test_context)
    unrelated_candidate = create_parsed_candidate(
        client,
        match_test_context,
        resume_text=UNRELATED_RESUME,
        full_name="Unrelated Fictional Candidate",
    )
    unrelated_job = create_parsed_job(
        client,
        match_test_context,
        description=UNRELATED_JOB_DESCRIPTION,
        title="Unrelated Fictional Job",
    )
    candidate_before = client.get(f"/candidates/{selected_candidate['id']}").json()
    candidate_parse_before = client.get(
        f"/candidates/{selected_candidate['id']}/parse-result",
    ).json()
    job_before = client.get(f"/jobs/{selected_job['id']}").json()
    job_parse_before = client.get(f"/jobs/{selected_job['id']}/parse-result").json()
    unrelated_candidate_before = client.get(
        f"/candidates/{unrelated_candidate['id']}",
    ).json()
    unrelated_job_before = client.get(f"/jobs/{unrelated_job['id']}").json()

    calculate_match(client, selected_candidate["id"], selected_job["id"])

    assert client.get(f"/candidates/{selected_candidate['id']}").json() == candidate_before
    assert (
        client.get(f"/candidates/{selected_candidate['id']}/parse-result").json()
        == candidate_parse_before
    )
    assert client.get(f"/jobs/{selected_job['id']}").json() == job_before
    assert client.get(f"/jobs/{selected_job['id']}/parse-result").json() == job_parse_before
    assert (
        client.get(f"/candidates/{unrelated_candidate['id']}").json()
        == unrelated_candidate_before
    )
    assert client.get(f"/jobs/{unrelated_job['id']}").json() == unrelated_job_before
