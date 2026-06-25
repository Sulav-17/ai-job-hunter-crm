from dataclasses import replace
import math
import numbers

import pytest
from sqlalchemy import delete, func, select

from backend.database.session import session_scope
from backend.models.application import Application, ApplicationStatusHistory
from backend.models.candidate import CandidateProfile
from backend.models.candidate_parse_result import CandidateParseResult, CandidateSkill
from backend.models.embedding import CandidateEmbedding, JobEmbedding, SemanticMatchResult
from backend.models.job import JobPosting
from backend.models.job_parse_result import JobParseResult
from backend.models.match_result import MatchResult, MatchSkillDetail
from backend.models.skill import JobSkill, Skill
from backend.models.tailoring import TailoringResult
from backend.services.demo_dataset import (
    DEMO_DATASET,
    DEMO_EMBEDDING_MODEL,
    DEMO_SEED_VERSION,
    DEMO_TAILORING_MODEL,
)
from backend.services.demo_seed import EMBEDDING_DIMENSIONS, seed_demo_dataset


@pytest.mark.integration
def test_demo_seed_is_idempotent_and_complete() -> None:
    with session_scope() as session:
        first_report = seed_demo_dataset(session, reset=True).as_dict()
        first_roots = _demo_root_ids(session)
        second_report = seed_demo_dataset(session).as_dict()
        second_roots = _demo_root_ids(session)

        assert first_report["seed_version"] == DEMO_SEED_VERSION
        assert second_report["seed_version"] == DEMO_SEED_VERSION
        assert first_report["candidates"] == 1
        assert first_report["jobs"] == 5
        assert first_report["applications"] == 5
        assert first_report["candidate_parse_results"] == 1
        assert first_report["job_parse_results"] == 5
        assert first_report["match_results"] == 5
        assert first_report["semantic_match_results"] == 5
        assert first_report["tailoring_results"] == 5
        assert first_report["candidate_embeddings"] == 1
        assert first_report["job_embeddings"] == 5
        assert first_report["status_history_rows"] >= 5
        assert second_report["applications"] == first_report["applications"]
        assert second_roots == first_roots

        statuses = set(
            session.scalars(
                select(Application.status).where(Application.is_demo.is_(True)),
            ),
        )
        assert statuses == {"saved", "applied", "interview", "rejected", "offer"}

        assert _count(session, CandidateSkill.id) >= 1
        assert _count(session, JobSkill.id) >= 1
        assert _count(session, MatchSkillDetail.id) >= 1


@pytest.mark.integration
def test_demo_seed_precomputed_outputs_are_valid_and_fictional() -> None:
    with session_scope() as session:
        seed_demo_dataset(session, reset=True)

        candidate = session.scalar(
            select(CandidateProfile).where(
                CandidateProfile.demo_seed_key == DEMO_DATASET.candidate.seed_key,
            ),
        )
        assert candidate is not None
        assert candidate.full_name == "Mira Quill"
        assert "example.invalid" in (candidate.resume_text or "")
        assert "Sulav" not in (candidate.resume_text or "")

        candidate_embedding = session.scalar(
            select(CandidateEmbedding).where(
                CandidateEmbedding.candidate_id == candidate.id,
            ),
        )
        assert candidate_embedding is not None
        assert candidate_embedding.model_name == DEMO_EMBEDDING_MODEL
        assert candidate_embedding.dimensions == EMBEDDING_DIMENSIONS
        assert len(candidate_embedding.embedding) == EMBEDDING_DIMENSIONS
        assert all(
            isinstance(value, numbers.Real) and math.isfinite(value)
            for value in candidate_embedding.embedding
        )

        demo_job_ids = list(
            session.scalars(
                select(JobPosting.id).where(JobPosting.is_demo.is_(True)),
            ),
        )
        job_embeddings = session.scalars(
            select(JobEmbedding).where(JobEmbedding.job_id.in_(demo_job_ids)),
        ).all()
        assert {embedding.model_name for embedding in job_embeddings} == {
            DEMO_EMBEDDING_MODEL,
        }
        assert all(embedding.dimensions == EMBEDDING_DIMENSIONS for embedding in job_embeddings)

        semantic_results = session.scalars(
            select(SemanticMatchResult).where(
                SemanticMatchResult.candidate_id == candidate.id,
            ),
        ).all()
        assert {result.model_name for result in semantic_results} == {DEMO_EMBEDDING_MODEL}
        assert all(0 <= result.semantic_score <= 100 for result in semantic_results)

        tailoring_results = session.scalars(
            select(TailoringResult).where(TailoringResult.candidate_id == candidate.id),
        ).all()
        assert {result.model_name for result in tailoring_results} == {DEMO_TAILORING_MODEL}
        for result in tailoring_results:
            assert "Human review required before using generated application text." in (
                result.warnings
            )
            for bullet in result.resume_bullets:
                assert bullet["supporting_evidence"].casefold() in (
                    candidate.resume_text or ""
                ).casefold()


@pytest.mark.integration
def test_demo_reset_preserves_non_demo_roots_and_shared_skills() -> None:
    with session_scope() as session:
        seed_demo_dataset(session, reset=True)
        skill_count_before = _count(session, Skill.id)
        candidate = CandidateProfile(
            full_name="Fictional Non Demo Candidate",
            resume_text="Fictional non-demo resume text.",
        )
        job = JobPosting(
            title="Fictional Non Demo Job",
            company="Non Demo Co",
            description="Fictional non-demo job description long enough for validation checks.",
        )
        session.add_all([candidate, job])
        session.flush()
        application = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            status="saved",
        )
        session.add(application)
        session.commit()
        non_demo_ids = (candidate.id, job.id, application.id)

        try:
            seed_demo_dataset(session, reset=True)

            assert session.get(CandidateProfile, non_demo_ids[0]) is not None
            assert session.get(JobPosting, non_demo_ids[1]) is not None
            assert session.get(Application, non_demo_ids[2]) is not None
            assert _count(session, Skill.id) >= skill_count_before
        finally:
            session.execute(delete(Application).where(Application.id == non_demo_ids[2]))
            session.execute(delete(JobPosting).where(JobPosting.id == non_demo_ids[1]))
            session.execute(
                delete(CandidateProfile).where(CandidateProfile.id == non_demo_ids[0]),
            )
            session.commit()


@pytest.mark.integration
def test_demo_seed_rolls_back_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    rollback_candidate = replace(
        DEMO_DATASET.candidate,
        seed_key=f"{DEMO_SEED_VERSION}:candidate:rollback",
        full_name="Rollback Demo Candidate",
    )
    rollback_job = replace(
        DEMO_DATASET.jobs[0],
        seed_key=f"{DEMO_SEED_VERSION}:job:rollback",
    )
    rollback_dataset = replace(
        DEMO_DATASET,
        candidate=rollback_candidate,
        jobs=(rollback_job,),
    )

    def fail_after_roots(*args, **kwargs) -> None:
        raise RuntimeError("forced rollback")

    monkeypatch.setattr(
        "backend.services.demo_seed._rebuild_matches_embeddings_and_tailoring",
        fail_after_roots,
    )

    with session_scope() as session:
        with pytest.raises(RuntimeError, match="forced rollback"):
            seed_demo_dataset(session, dataset=rollback_dataset)

        assert (
            session.scalar(
                select(CandidateProfile).where(
                    CandidateProfile.demo_seed_key == rollback_candidate.seed_key,
                ),
            )
            is None
        )


def _demo_root_ids(session) -> dict[str, tuple[int, ...]]:
    return {
        "candidates": tuple(
            session.scalars(
                select(CandidateProfile.id)
                .where(CandidateProfile.is_demo.is_(True))
                .order_by(CandidateProfile.demo_seed_key),
            ),
        ),
        "jobs": tuple(
            session.scalars(
                select(JobPosting.id)
                .where(JobPosting.is_demo.is_(True))
                .order_by(JobPosting.demo_seed_key),
            ),
        ),
        "applications": tuple(
            session.scalars(
                select(Application.id)
                .where(Application.is_demo.is_(True))
                .order_by(Application.demo_seed_key),
            ),
        ),
    }


def _count(session, column) -> int:
    return session.scalar(select(func.count(column))) or 0
