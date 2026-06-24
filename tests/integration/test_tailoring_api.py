from collections.abc import Generator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from backend.api.routes.embeddings import get_embedding_provider
from backend.api.routes.tailoring import get_generation_provider
from backend.database.session import session_scope
from backend.main import app
from backend.models.application import Application, ApplicationStatusHistory
from backend.models.candidate import CandidateProfile
from backend.models.candidate_parse_result import CandidateParseResult, CandidateSkill
from backend.models.embedding import CandidateEmbedding, JobEmbedding, SemanticMatchResult
from backend.models.job import JobPosting
from backend.models.job_parse_result import JobParseResult
from backend.models.match_result import MatchResult, MatchSkillDetail
from backend.models.skill import JobSkill, Skill
from backend.models.tailoring import TailoringResult
from backend.services.embedding_provider import EmbeddingProviderError
from backend.services.generation_provider import (
    GenerationPrompt,
    GenerationProviderError,
    MalformedGenerationOutputError,
)


CANDIDATE_RESUME = (
    "Fictional tailoring resume. Built Python dashboards with SQL and Power BI. "
    "Led documentation for internal reporting workflows. "
    "Completed a bachelor's degree for fictional testing."
)
UPDATED_CANDIDATE_RESUME = (
    "Fictional updated tailoring resume. Built FastAPI services with PostgreSQL. "
    "Documented API workflows for fictional local teams."
)
JOB_DESCRIPTION = (
    "Requirements: Python and SQL with 5+ years of experience. "
    "Bachelor's degree required for this fictional tailoring role. "
    "Preferred qualifications: Power BI and documentation experience."
)
UPDATED_JOB_DESCRIPTION = (
    "Requirements: FastAPI and PostgreSQL with 3+ years of experience. "
    "Bachelor's degree required for this fictional tailoring role."
)
TEST_NORMALIZED_SKILLS = {
    "python",
    "sql",
    "power_bi",
    "documentation",
    "fastapi",
    "postgresql",
}


class FakeGenerationProvider:
    def __init__(self, model_identity: str = "fake:qwen3-test") -> None:
        self._model_identity = model_identity
        self.calls: list[GenerationPrompt] = []
        self.fail = False
        self.malformed = False
        self.invalid_evidence = False

    @property
    def model_identity(self) -> str:
        return self._model_identity

    @model_identity.setter
    def model_identity(self, value: str) -> None:
        self._model_identity = value

    def generate(self, prompt: GenerationPrompt) -> dict[str, Any]:
        self.calls.append(prompt)
        if self.fail:
            raise GenerationProviderError("provider unavailable")
        if self.malformed:
            raise MalformedGenerationOutputError("invalid output")
        payload = _valid_tailoring_payload(len(self.calls))
        if self.invalid_evidence:
            payload["resume_bullets"][0]["supporting_evidence"] = "Managed Kubernetes"
        return payload


class FakeEmbeddingProvider:
    @property
    def model_identity(self) -> str:
        return "fake:test-embedding"

    def embed(self, source_text: str) -> list[float]:
        if not source_text:
            raise EmbeddingProviderError("provider unavailable")
        return [float(len(source_text)), 1.0, 2.0]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def fake_generation_provider() -> Generator[FakeGenerationProvider, None, None]:
    provider = FakeGenerationProvider()
    app.dependency_overrides[get_generation_provider] = lambda: provider
    try:
        yield provider
    finally:
        app.dependency_overrides.pop(get_generation_provider, None)


@pytest.fixture
def fake_embedding_provider() -> Generator[FakeEmbeddingProvider, None, None]:
    provider = FakeEmbeddingProvider()
    app.dependency_overrides[get_embedding_provider] = lambda: provider
    try:
        yield provider
    finally:
        app.dependency_overrides.pop(get_embedding_provider, None)


@pytest.fixture
def tailoring_test_context() -> Generator[dict[str, Any], None, None]:
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
        "application_ids": [],
        "existing_skill_names": existing_skill_names,
        "starting_counts": starting_counts,
    }
    try:
        yield context
    finally:
        with session_scope() as session:
            application_ids = cast(list[int], context["application_ids"])
            candidate_ids = cast(list[int], context["candidate_ids"])
            job_ids = cast(list[int], context["job_ids"])
            if application_ids:
                session.execute(delete(Application).where(Application.id.in_(application_ids)))
            if candidate_ids:
                session.execute(
                    delete(CandidateProfile).where(CandidateProfile.id.in_(candidate_ids)),
                )
            if job_ids:
                session.execute(delete(JobPosting).where(JobPosting.id.in_(job_ids)))
            session.commit()

            removable_skill_names = TEST_NORMALIZED_SKILLS - cast(
                set[str],
                context["existing_skill_names"],
            )
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

        assert ending_counts == context["starting_counts"]


@pytest.mark.integration
def test_generate_retrieve_reuse_and_forced_regeneration(
    client: TestClient,
    fake_generation_provider: FakeGenerationProvider,
    tailoring_test_context: dict[str, Any],
) -> None:
    candidate, job = create_parsed_candidate_job_pair(client, tailoring_test_context)

    generated = client.post(f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring")
    retrieved = client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring-result",
    )
    reused = client.post(f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring")
    regenerated = client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring",
        json={"regenerate": True},
    )

    assert generated.status_code == 200
    assert retrieved.status_code == 200
    assert reused.status_code == 200
    assert regenerated.status_code == 200
    assert retrieved.json() == generated.json()
    assert reused.json() == generated.json()
    assert regenerated.json()["tailored_summary"] != generated.json()["tailored_summary"]
    assert len(fake_generation_provider.calls) == 2
    assert generated.json()["model_name"] == "fake:qwen3-test"
    assert generated.json()["prompt_version"] == "tailoring-v1"
    assert generated.json()["stale"] is False
    assert "resume_text" not in generated.json()
    assert "professional_summary" not in generated.json()
    assert "description" not in generated.json()
    assert "prompt" not in generated.json()
    assert "provider" not in generated.json()
    with session_scope() as session:
        result = session.scalar(
            select(TailoringResult).where(
                TailoringResult.candidate_id == candidate["id"],
                TailoringResult.job_id == job["id"],
            ),
        )
        result_count = session.scalar(
            select(func.count(TailoringResult.id)).where(
                TailoringResult.candidate_id == candidate["id"],
                TailoringResult.job_id == job["id"],
            ),
        )
    assert result_count == 1
    assert isinstance(result.resume_bullets, list)
    assert isinstance(result.keywords_used, list)
    assert isinstance(result.warnings, list)


@pytest.mark.integration
def test_stale_detection_for_source_context_and_model_changes(
    client: TestClient,
    fake_generation_provider: FakeGenerationProvider,
    tailoring_test_context: dict[str, Any],
) -> None:
    candidate, job = create_parsed_candidate_job_pair(client, tailoring_test_context)
    assert client.post(f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring").status_code == 200

    assert client.patch(
        f"/candidates/{candidate['id']}",
        json={"headline": "Updated Fictional Analyst"},
    ).status_code == 200
    assert client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring-result",
    ).json()["stale"] is True
    assert client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring",
        json={"regenerate": True},
    ).status_code == 200

    assert client.patch(
        f"/jobs/{job['id']}",
        json={"location": "Remote"},
    ).status_code == 200
    assert client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring-result",
    ).json()["stale"] is True
    assert client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring",
        json={"regenerate": True},
    ).status_code == 200

    with session_scope() as session:
        parse_result = session.scalar(
            select(JobParseResult).where(JobParseResult.job_id == job["id"]),
        )
        parse_result.minimum_years_experience = 10
        session.commit()
    assert client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring-result",
    ).json()["stale"] is True
    assert client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring",
        json={"regenerate": True},
    ).status_code == 200

    fake_generation_provider.model_identity = "fake:other-model"
    assert client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring-result",
    ).json()["stale"] is True


@pytest.mark.integration
def test_provider_and_validation_failures_preserve_previous_result(
    client: TestClient,
    fake_generation_provider: FakeGenerationProvider,
    tailoring_test_context: dict[str, Any],
) -> None:
    candidate, job = create_parsed_candidate_job_pair(client, tailoring_test_context)
    original = client.post(f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring")
    assert original.status_code == 200

    fake_generation_provider.fail = True
    failed = client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring",
        json={"regenerate": True},
    )
    fake_generation_provider.fail = False
    assert failed.status_code == 502
    assert failed.json() == {"detail": "Generation provider unavailable"}
    assert client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring-result",
    ).json() == original.json()

    fake_generation_provider.invalid_evidence = True
    invalid = client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring",
        json={"regenerate": True},
    )
    fake_generation_provider.invalid_evidence = False
    assert invalid.status_code == 502
    assert invalid.json() == {"detail": "Generation provider returned invalid output"}
    assert client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring-result",
    ).json() == original.json()

    fake_generation_provider.malformed = True
    malformed = client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring",
        json={"regenerate": True},
    )
    assert malformed.status_code == 502
    assert malformed.json() == {"detail": "Generation provider returned invalid output"}
    assert client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring-result",
    ).json() == original.json()


@pytest.mark.integration
def test_missing_records_and_prerequisites(
    client: TestClient,
    fake_generation_provider: FakeGenerationProvider,
    tailoring_test_context: dict[str, Any],
) -> None:
    candidate = create_candidate(client, tailoring_test_context)
    job = create_job(client, tailoring_test_context)
    blank_candidate = create_candidate(
        client,
        tailoring_test_context,
        resume_text="   ",
    )
    parsed_candidate = create_candidate(client, tailoring_test_context)
    assert client.post(f"/candidates/{parsed_candidate['id']}/parse").status_code == 200

    missing_candidate = client.post(f"/candidates/999999999/jobs/{job['id']}/tailoring")
    missing_job = client.post(f"/candidates/{candidate['id']}/jobs/999999999/tailoring")
    missing_resume = client.post(
        f"/candidates/{blank_candidate['id']}/jobs/{job['id']}/tailoring",
    )
    unparsed_candidate = client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring",
    )
    unparsed_job = client.post(
        f"/candidates/{parsed_candidate['id']}/jobs/{job['id']}/tailoring",
    )
    missing_result = client.get(
        f"/candidates/{parsed_candidate['id']}/jobs/{job['id']}/tailoring-result",
    )
    unknown_field = client.post(
        f"/candidates/{parsed_candidate['id']}/jobs/{job['id']}/tailoring",
        json={"unexpected": True},
    )

    assert missing_candidate.status_code == 404
    assert missing_candidate.json() == {"detail": "Candidate not found"}
    assert missing_job.status_code == 404
    assert missing_job.json() == {"detail": "Job not found"}
    assert missing_resume.status_code == 409
    assert missing_resume.json() == {"detail": "Candidate resume text is required"}
    assert unparsed_candidate.status_code == 409
    assert unparsed_candidate.json() == {
        "detail": "Candidate must be parsed before tailoring",
    }
    assert unparsed_job.status_code == 409
    assert unparsed_job.json() == {"detail": "Job must be parsed before tailoring"}
    assert missing_result.status_code == 404
    assert missing_result.json() == {"detail": "Tailoring result not found"}
    assert unknown_field.status_code == 422


@pytest.mark.integration
def test_candidate_and_job_deletion_cascades_tailoring_results(
    client: TestClient,
    fake_generation_provider: FakeGenerationProvider,
    tailoring_test_context: dict[str, Any],
) -> None:
    candidate, job = create_parsed_candidate_job_pair(client, tailoring_test_context)
    assert client.post(f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring").status_code == 200

    assert client.delete(f"/candidates/{candidate['id']}").status_code == 204
    with session_scope() as session:
        tailoring_count = session.scalar(
            select(func.count(TailoringResult.id)).where(
                TailoringResult.candidate_id == candidate["id"],
            ),
        )
    assert tailoring_count == 0

    second_candidate, second_job = create_parsed_candidate_job_pair(
        client,
        tailoring_test_context,
    )
    assert client.post(
        f"/candidates/{second_candidate['id']}/jobs/{second_job['id']}/tailoring",
    ).status_code == 200
    assert client.delete(f"/jobs/{second_job['id']}").status_code == 204
    with session_scope() as session:
        tailoring_count = session.scalar(
            select(func.count(TailoringResult.id)).where(
                TailoringResult.job_id == second_job["id"],
            ),
        )
    assert tailoring_count == 0


@pytest.mark.integration
def test_tailoring_preserves_source_records(
    client: TestClient,
    fake_generation_provider: FakeGenerationProvider,
    fake_embedding_provider: FakeEmbeddingProvider,
    tailoring_test_context: dict[str, Any],
) -> None:
    candidate, job = create_parsed_candidate_job_pair(client, tailoring_test_context)
    assert client.post(f"/candidates/{candidate['id']}/jobs/{job['id']}/match").status_code == 200
    assert client.post(f"/candidates/{candidate['id']}/embedding").status_code == 200
    assert client.post(f"/jobs/{job['id']}/embedding").status_code == 200
    assert client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/semantic-match",
    ).status_code == 200
    application = client.post(
        "/applications",
        json={"candidate_id": candidate["id"], "job_id": job["id"]},
    )
    assert application.status_code == 201
    cast(list[int], tailoring_test_context["application_ids"]).append(application.json()["id"])
    before_counts = _owned_record_counts(candidate["id"], job["id"])

    assert client.post(f"/candidates/{candidate['id']}/jobs/{job['id']}/tailoring").status_code == 200

    after_counts = _owned_record_counts(candidate["id"], job["id"])
    for key in (
        "candidate_parse_results",
        "candidate_skills",
        "job_parse_results",
        "job_skills",
        "match_results",
        "match_skill_details",
        "candidate_embeddings",
        "job_embeddings",
        "semantic_match_results",
        "applications",
        "application_status_history",
        "shared_skills",
    ):
        assert after_counts[key] == before_counts[key]


def create_parsed_candidate_job_pair(
    client: TestClient,
    context: dict[str, Any],
) -> tuple[dict, dict]:
    candidate = create_candidate(client, context)
    job = create_job(client, context)
    assert client.post(f"/candidates/{candidate['id']}/parse").status_code == 200
    assert client.post(f"/jobs/{job['id']}/parse").status_code == 200
    return candidate, job


def create_candidate(
    client: TestClient,
    context: dict[str, Any],
    resume_text: str | None = CANDIDATE_RESUME,
) -> dict:
    response = client.post(
        "/candidates",
        json={
            "full_name": "Fictional Tailoring Candidate",
            "headline": "Fictional Analyst",
            "location": "Toronto, ON",
            "professional_summary": "Fictional profile for tailoring tests.",
            "years_experience": 4,
            "resume_text": resume_text,
        },
    )
    assert response.status_code == 201
    candidate = response.json()
    cast(list[int], context["candidate_ids"]).append(candidate["id"])
    return candidate


def create_job(client: TestClient, context: dict[str, Any]) -> dict:
    response = client.post(
        "/jobs",
        json={
            "title": "Fictional Tailoring Job",
            "company": "Northstar Labs",
            "location": "Toronto, ON",
            "employment_type": "full_time",
            "work_mode": "hybrid",
            "source_url": "https://example.com/jobs/fictional-tailoring-job",
            "description": JOB_DESCRIPTION,
        },
    )
    assert response.status_code == 201
    job = response.json()
    cast(list[int], context["job_ids"]).append(job["id"])
    return job


def _valid_tailoring_payload(call_number: int) -> dict[str, Any]:
    return {
        "tailored_summary": f"Fictional tailored summary version {call_number}.",
        "resume_bullets": [
            {
                "text": "Built Python dashboards with SQL for fictional reporting workflows.",
                "supporting_evidence": "Built Python dashboards with SQL",
                "keywords": ["Python", "SQL"],
            },
            {
                "text": "Used Power BI in fictional analytics work.",
                "supporting_evidence": "SQL and Power BI",
                "keywords": ["Power BI", "SQL"],
            },
            {
                "text": "Documented internal reporting workflows.",
                "supporting_evidence": "Led documentation for internal reporting workflows.",
                "keywords": ["documentation"],
            },
        ],
        "cover_letter": "Dear Hiring Team,\nThis is fictional generated tailoring text.",
        "keywords_used": ["SQL", "Python", "Power BI", "documentation"],
        "warnings": ["Review before use."],
    }


def _record_counts(session) -> dict[str, int]:
    return {
        "candidates": session.scalar(select(func.count(CandidateProfile.id))) or 0,
        "jobs": session.scalar(select(func.count(JobPosting.id))) or 0,
        "skills": session.scalar(select(func.count(Skill.id))) or 0,
        "candidate_parse_results": session.scalar(
            select(func.count(CandidateParseResult.id)),
        )
        or 0,
        "candidate_skills": session.scalar(select(func.count(CandidateSkill.id))) or 0,
        "job_parse_results": session.scalar(select(func.count(JobParseResult.id))) or 0,
        "job_skills": session.scalar(select(func.count(JobSkill.id))) or 0,
        "match_results": session.scalar(select(func.count(MatchResult.id))) or 0,
        "match_skill_details": session.scalar(select(func.count(MatchSkillDetail.id))) or 0,
        "applications": session.scalar(select(func.count(Application.id))) or 0,
        "application_status_history": session.scalar(
            select(func.count(ApplicationStatusHistory.id)),
        )
        or 0,
        "candidate_embeddings": session.scalar(select(func.count(CandidateEmbedding.id)))
        or 0,
        "job_embeddings": session.scalar(select(func.count(JobEmbedding.id))) or 0,
        "semantic_match_results": session.scalar(
            select(func.count(SemanticMatchResult.id)),
        )
        or 0,
        "tailoring_results": session.scalar(select(func.count(TailoringResult.id))) or 0,
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


def _owned_record_counts(candidate_id: int, job_id: int) -> dict[str, int]:
    with session_scope() as session:
        return {
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
            "candidate_embeddings": session.scalar(
                select(func.count(CandidateEmbedding.id)).where(
                    CandidateEmbedding.candidate_id == candidate_id,
                ),
            )
            or 0,
            "job_embeddings": session.scalar(
                select(func.count(JobEmbedding.id)).where(JobEmbedding.job_id == job_id),
            )
            or 0,
            "semantic_match_results": session.scalar(
                select(func.count(SemanticMatchResult.id)).where(
                    SemanticMatchResult.candidate_id == candidate_id,
                    SemanticMatchResult.job_id == job_id,
                ),
            )
            or 0,
            "applications": session.scalar(
                select(func.count(Application.id)).where(
                    Application.candidate_id == candidate_id,
                    Application.job_id == job_id,
                ),
            )
            or 0,
            "application_status_history": session.scalar(
                select(func.count(ApplicationStatusHistory.id))
                .join(Application)
                .where(
                    Application.candidate_id == candidate_id,
                    Application.job_id == job_id,
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
