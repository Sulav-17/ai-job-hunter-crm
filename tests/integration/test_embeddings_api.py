from collections.abc import Callable, Generator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from backend.api.routes.embeddings import get_embedding_provider
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
from backend.services.embedding_provider import EmbeddingProviderError


CANDIDATE_RESUME = (
    "Fictional embedding candidate resume. Built dashboards with Python, SQL, "
    "and Power BI. More than 4 years of experience. Bachelor's degree completed."
)
UPDATED_CANDIDATE_RESUME = (
    "Fictional updated embedding resume. Built APIs with FastAPI and Docker. "
    "More than 6 years of experience. Master's degree completed."
)
JOB_DESCRIPTION = (
    "Requirements: Python and SQL with 3+ years of experience. "
    "Bachelor's degree required for this fictional embedding role. "
    "Preferred qualifications: Power BI is nice to have."
)
UPDATED_JOB_DESCRIPTION = (
    "Requirements: FastAPI and Docker with 5+ years of experience. "
    "Master's degree required for this fictional embedding role."
)
TEST_NORMALIZED_SKILLS = {
    "python",
    "sql",
    "power_bi",
    "fastapi",
    "docker",
}


class FakeEmbeddingProvider:
    def __init__(
        self,
        *,
        model_identity: str = "fake:test-embedding",
        vector_factory: Callable[[str], list[float]] | None = None,
        fail: bool = False,
    ) -> None:
        self._model_identity = model_identity
        self.vector_factory = vector_factory or self._default_vector
        self.fail = fail
        self.calls: list[str] = []

    @property
    def model_identity(self) -> str:
        return self._model_identity

    def embed(self, source_text: str) -> list[float]:
        self.calls.append(source_text)
        if self.fail:
            raise EmbeddingProviderError("provider unavailable")
        return self.vector_factory(source_text)

    def _default_vector(self, source_text: str) -> list[float]:
        text_length = float(len(source_text))
        checksum = float(sum(ord(character) for character in source_text) % 1000)
        return [text_length, checksum, 1.0]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def fake_provider() -> Generator[FakeEmbeddingProvider, None, None]:
    provider = FakeEmbeddingProvider()
    app.dependency_overrides[get_embedding_provider] = lambda: provider
    try:
        yield provider
    finally:
        app.dependency_overrides.pop(get_embedding_provider, None)


@pytest.fixture
def embedding_test_context() -> Generator[dict[str, Any], None, None]:
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
        candidate_ids = cast(list[int], context["candidate_ids"])
        job_ids = cast(list[int], context["job_ids"])
        application_ids = cast(list[int], context["application_ids"])
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

        assert ending_counts == context["starting_counts"]


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
    resume_text: str | None = CANDIDATE_RESUME,
) -> dict:
    response = client.post(
        "/candidates",
        json={
            "full_name": "Fictional Embedding Candidate",
            "headline": "Fictional Analyst",
            "location": "Toronto, ON",
            "professional_summary": "Fictional profile for embedding tests.",
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
            "title": "Fictional Embedding Job",
            "company": "Northstar Labs",
            "location": "Toronto, ON",
            "employment_type": "full_time",
            "work_mode": "hybrid",
            "source_url": "https://example.com/jobs/fictional-embedding-job",
            "description": JOB_DESCRIPTION,
        },
    )
    assert response.status_code == 201
    job = response.json()
    cast(list[int], context["job_ids"]).append(job["id"])
    return job


def create_application_record(
    client: TestClient,
    context: dict[str, Any],
    candidate_id: int,
    job_id: int,
) -> dict:
    response = client.post(
        "/applications",
        json={"candidate_id": candidate_id, "job_id": job_id},
    )
    assert response.status_code == 201
    application = response.json()
    cast(list[int], context["application_ids"]).append(application["id"])
    return application


def create_candidate_job_pair(
    client: TestClient,
    context: dict[str, Any],
) -> tuple[dict, dict]:
    return create_candidate(client, context), create_job(client, context)


@pytest.mark.integration
def test_candidate_and_job_embedding_metadata(
    client: TestClient,
    fake_provider: FakeEmbeddingProvider,
    embedding_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_job_pair(client, embedding_test_context)

    candidate_response = client.post(f"/candidates/{candidate['id']}/embedding")
    candidate_get = client.get(f"/candidates/{candidate['id']}/embedding")
    job_response = client.post(f"/jobs/{job['id']}/embedding")
    job_get = client.get(f"/jobs/{job['id']}/embedding")

    assert candidate_response.status_code == 200
    assert candidate_get.status_code == 200
    assert candidate_get.json() == candidate_response.json()
    assert candidate_response.json()["candidate_id"] == candidate["id"]
    assert candidate_response.json()["model_name"] == fake_provider.model_identity
    assert candidate_response.json()["dimensions"] == 3
    assert candidate_response.json()["stale"] is False
    assert "embedding" not in candidate_response.json()
    assert "resume_text" not in candidate_response.json()
    assert "professional_summary" not in candidate_response.json()

    assert job_response.status_code == 200
    assert job_get.status_code == 200
    assert job_get.json() == job_response.json()
    assert job_response.json()["job_id"] == job["id"]
    assert job_response.json()["dimensions"] == 3
    assert "embedding" not in job_response.json()
    assert "description" not in job_response.json()


@pytest.mark.integration
def test_repeated_embedding_reuses_current_metadata(
    client: TestClient,
    fake_provider: FakeEmbeddingProvider,
    embedding_test_context: dict[str, Any],
) -> None:
    candidate = create_candidate(client, embedding_test_context)

    first = client.post(f"/candidates/{candidate['id']}/embedding")
    second = client.post(f"/candidates/{candidate['id']}/embedding")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(fake_provider.calls) == 1
    with session_scope() as session:
        embedding_count = session.scalar(
            select(func.count(CandidateEmbedding.id)).where(
                CandidateEmbedding.candidate_id == candidate["id"],
            ),
        )
    assert embedding_count == 1


@pytest.mark.integration
def test_changed_source_updates_embedding_and_changed_model_marks_stale(
    client: TestClient,
    fake_provider: FakeEmbeddingProvider,
    embedding_test_context: dict[str, Any],
) -> None:
    candidate = create_candidate(client, embedding_test_context)
    original = client.post(f"/candidates/{candidate['id']}/embedding").json()

    update_response = client.patch(
        f"/candidates/{candidate['id']}",
        json={"resume_text": UPDATED_CANDIDATE_RESUME},
    )
    assert update_response.status_code == 200
    stale_response = client.get(f"/candidates/{candidate['id']}/embedding")
    updated = client.post(f"/candidates/{candidate['id']}/embedding")

    assert stale_response.status_code == 200
    assert stale_response.json()["stale"] is True
    assert updated.status_code == 200
    assert updated.json()["source_hash"] != original["source_hash"]

    new_model_provider = FakeEmbeddingProvider(model_identity="fake:new-model")
    app.dependency_overrides[get_embedding_provider] = lambda: new_model_provider
    model_stale = client.get(f"/candidates/{candidate['id']}/embedding")
    assert model_stale.status_code == 200
    assert model_stale.json()["stale"] is True


@pytest.mark.integration
def test_provider_failure_returns_502_and_preserves_previous_embedding(
    client: TestClient,
    fake_provider: FakeEmbeddingProvider,
    embedding_test_context: dict[str, Any],
) -> None:
    candidate = create_candidate(client, embedding_test_context)
    original = client.post(f"/candidates/{candidate['id']}/embedding").json()
    assert client.patch(
        f"/candidates/{candidate['id']}",
        json={"resume_text": UPDATED_CANDIDATE_RESUME},
    ).status_code == 200
    fake_provider.fail = True

    failed = client.post(f"/candidates/{candidate['id']}/embedding")
    fake_provider.fail = False
    current = client.get(f"/candidates/{candidate['id']}/embedding")

    assert failed.status_code == 502
    assert failed.json() == {"detail": "Embedding provider unavailable"}
    assert current.status_code == 200
    assert current.json()["source_hash"] == original["source_hash"]
    assert current.json()["stale"] is True


@pytest.mark.integration
def test_semantic_match_calculation_and_recalculation(
    client: TestClient,
    fake_provider: FakeEmbeddingProvider,
    embedding_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_job_pair(client, embedding_test_context)
    assert client.post(f"/candidates/{candidate['id']}/embedding").status_code == 200
    assert client.post(f"/jobs/{job['id']}/embedding").status_code == 200

    calculated = client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/semantic-match",
    )
    retrieved = client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/semantic-match-result",
    )
    recalculated = client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/semantic-match",
    )

    assert calculated.status_code == 200
    assert retrieved.status_code == 200
    assert retrieved.json() == calculated.json()
    assert recalculated.status_code == 200
    assert recalculated.json()["semantic_score"] == calculated.json()["semantic_score"]
    assert "resume_text" not in calculated.json()
    assert "description" not in calculated.json()
    with session_scope() as session:
        result_count = session.scalar(
            select(func.count(SemanticMatchResult.id)).where(
                SemanticMatchResult.candidate_id == candidate["id"],
                SemanticMatchResult.job_id == job["id"],
            ),
        )
    assert result_count == 1


@pytest.mark.integration
def test_semantic_match_prerequisites(
    client: TestClient,
    fake_provider: FakeEmbeddingProvider,
    embedding_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_job_pair(client, embedding_test_context)

    missing_candidate_embedding = client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/semantic-match",
    )
    assert client.post(f"/candidates/{candidate['id']}/embedding").status_code == 200
    missing_job_embedding = client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/semantic-match",
    )
    assert client.post(f"/jobs/{job['id']}/embedding").status_code == 200
    assert client.patch(
        f"/jobs/{job['id']}",
        json={"description": UPDATED_JOB_DESCRIPTION},
    ).status_code == 200
    stale_job_embedding = client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/semantic-match",
    )

    assert missing_candidate_embedding.status_code == 409
    assert missing_candidate_embedding.json() == {
        "detail": "Candidate embedding is missing or stale",
    }
    assert missing_job_embedding.status_code == 409
    assert missing_job_embedding.json() == {
        "detail": "Job embedding is missing or stale",
    }
    assert stale_job_embedding.status_code == 409
    assert stale_job_embedding.json() == {"detail": "Job embedding is missing or stale"}


@pytest.mark.integration
def test_dimension_incompatibility_returns_409(
    client: TestClient,
    fake_provider: FakeEmbeddingProvider,
    embedding_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_job_pair(client, embedding_test_context)
    fake_provider.vector_factory = lambda source_text: [1.0, 2.0]
    assert client.post(f"/candidates/{candidate['id']}/embedding").status_code == 200
    fake_provider.vector_factory = lambda source_text: [1.0, 2.0, 3.0]
    assert client.post(f"/jobs/{job['id']}/embedding").status_code == 200

    response = client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/semantic-match",
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Candidate and job embeddings are incompatible",
    }


@pytest.mark.integration
def test_missing_records_and_missing_resume_errors(
    client: TestClient,
    fake_provider: FakeEmbeddingProvider,
    embedding_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_job_pair(client, embedding_test_context)
    blank_resume_candidate = create_candidate(
        client,
        embedding_test_context,
        resume_text="   ",
    )

    missing_candidate = client.post("/candidates/999999999/embedding")
    missing_job = client.post("/jobs/999999999/embedding")
    missing_resume = client.post(
        f"/candidates/{blank_resume_candidate['id']}/embedding",
    )
    missing_candidate_metadata = client.get(
        f"/candidates/{blank_resume_candidate['id']}/embedding",
    )
    missing_job_metadata = client.get(f"/jobs/{job['id']}/embedding")
    missing_semantic = client.get(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/semantic-match-result",
    )

    assert missing_candidate.status_code == 404
    assert missing_candidate.json() == {"detail": "Candidate not found"}
    assert missing_job.status_code == 404
    assert missing_job.json() == {"detail": "Job not found"}
    assert missing_resume.status_code == 409
    assert missing_resume.json() == {"detail": "Candidate resume text is required"}
    assert missing_candidate_metadata.status_code == 404
    assert missing_candidate_metadata.json() == {
        "detail": "Candidate embedding not found",
    }
    assert missing_job_metadata.status_code == 404
    assert missing_job_metadata.json() == {"detail": "Job embedding not found"}
    assert missing_semantic.status_code == 404
    assert missing_semantic.json() == {"detail": "Semantic match result not found"}


@pytest.mark.integration
def test_candidate_and_job_deletion_cascades_embedding_and_semantic_rows(
    client: TestClient,
    fake_provider: FakeEmbeddingProvider,
    embedding_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_job_pair(client, embedding_test_context)
    assert client.post(f"/candidates/{candidate['id']}/embedding").status_code == 200
    assert client.post(f"/jobs/{job['id']}/embedding").status_code == 200
    assert client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/semantic-match",
    ).status_code == 200

    assert client.delete(f"/candidates/{candidate['id']}").status_code == 204
    with session_scope() as session:
        candidate_embedding_count = session.scalar(
            select(func.count(CandidateEmbedding.id)).where(
                CandidateEmbedding.candidate_id == candidate["id"],
            ),
        )
        semantic_count = session.scalar(
            select(func.count(SemanticMatchResult.id)).where(
                SemanticMatchResult.candidate_id == candidate["id"],
            ),
        )
    assert candidate_embedding_count == 0
    assert semantic_count == 0

    second_candidate, second_job = create_candidate_job_pair(
        client,
        embedding_test_context,
    )
    assert client.post(f"/candidates/{second_candidate['id']}/embedding").status_code == 200
    assert client.post(f"/jobs/{second_job['id']}/embedding").status_code == 200
    assert client.post(
        f"/candidates/{second_candidate['id']}/jobs/{second_job['id']}/semantic-match",
    ).status_code == 200

    assert client.delete(f"/jobs/{second_job['id']}").status_code == 204
    with session_scope() as session:
        job_embedding_count = session.scalar(
            select(func.count(JobEmbedding.id)).where(JobEmbedding.job_id == second_job["id"]),
        )
        semantic_count = session.scalar(
            select(func.count(SemanticMatchResult.id)).where(
                SemanticMatchResult.job_id == second_job["id"],
            ),
        )
    assert job_embedding_count == 0
    assert semantic_count == 0


@pytest.mark.integration
def test_embedding_operations_preserve_existing_parse_match_application_and_skills(
    client: TestClient,
    fake_provider: FakeEmbeddingProvider,
    embedding_test_context: dict[str, Any],
) -> None:
    candidate, job = create_candidate_job_pair(client, embedding_test_context)
    assert client.post(f"/candidates/{candidate['id']}/parse").status_code == 200
    assert client.post(f"/jobs/{job['id']}/parse").status_code == 200
    assert client.post(f"/candidates/{candidate['id']}/jobs/{job['id']}/match").status_code == 200
    create_application_record(client, embedding_test_context, candidate["id"], job["id"])
    before_counts = _owned_record_counts(candidate["id"], job["id"])

    assert client.post(f"/candidates/{candidate['id']}/embedding").status_code == 200
    assert client.post(f"/jobs/{job['id']}/embedding").status_code == 200
    assert client.post(
        f"/candidates/{candidate['id']}/jobs/{job['id']}/semantic-match",
    ).status_code == 200

    after_counts = _owned_record_counts(candidate["id"], job["id"])
    for key in (
        "candidate_parse_results",
        "candidate_skills",
        "job_parse_results",
        "job_skills",
        "match_results",
        "match_skill_details",
        "applications",
        "application_status_history",
        "shared_skills",
    ):
        assert after_counts[key] == before_counts[key]


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
