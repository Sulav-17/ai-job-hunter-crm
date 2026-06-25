from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from collections.abc import Iterable

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models.application import Application, ApplicationStatusHistory
from backend.models.candidate import CandidateProfile
from backend.models.candidate_parse_result import CandidateParseResult, CandidateSkill
from backend.models.embedding import CandidateEmbedding, JobEmbedding, SemanticMatchResult
from backend.models.job import JobPosting
from backend.models.job_parse_result import JobParseResult
from backend.models.match_result import MatchResult, MatchSkillDetail
from backend.models.skill import JobSkill, Skill
from backend.models.tailoring import TailoringResult
from backend.services.candidate_parser import ParsedCandidate, parse_candidate_resume
from backend.services.demo_dataset import (
    DEMO_DATASET,
    DEMO_EMBEDDING_MODEL,
    DEMO_SEED_VERSION,
    DEMO_TAILORING_MODEL,
    DemoDataset,
    DemoJob,
)
from backend.services.job_parser import ParsedJob, parse_job_description
from backend.services.match_scorer import (
    CandidateMatchInput,
    JobMatchInput,
    MatchScoreResult,
    MatchSkillInput,
    calculate_match_score,
)
from backend.services.semantic_similarity import (
    build_candidate_embedding_source,
    build_job_embedding_source,
    cosine_similarity,
    semantic_score_from_similarity,
    source_hash as embedding_source_hash,
)
from backend.services.tailoring_prompt import (
    PROMPT_VERSION,
    build_candidate_source,
    build_job_source,
    build_match_context,
    build_sources,
    deterministic_gap_warnings,
    validate_tailoring_output,
)

SEED_TIMESTAMP = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)
EMBEDDING_DIMENSIONS = 3


@dataclass(frozen=True)
class DemoSeedReport:
    seed_version: str
    reset: bool
    candidates: int
    jobs: int
    applications: int
    candidate_parse_results: int
    job_parse_results: int
    candidate_skills: int
    job_skills: int
    match_results: int
    semantic_match_results: int
    tailoring_results: int
    candidate_embeddings: int
    job_embeddings: int
    status_history_rows: int

    def as_dict(self) -> dict[str, int | str | bool]:
        return {
            "seed_version": self.seed_version,
            "reset": self.reset,
            "candidates": self.candidates,
            "jobs": self.jobs,
            "applications": self.applications,
            "candidate_parse_results": self.candidate_parse_results,
            "job_parse_results": self.job_parse_results,
            "candidate_skills": self.candidate_skills,
            "job_skills": self.job_skills,
            "match_results": self.match_results,
            "semantic_match_results": self.semantic_match_results,
            "tailoring_results": self.tailoring_results,
            "candidate_embeddings": self.candidate_embeddings,
            "job_embeddings": self.job_embeddings,
            "status_history_rows": self.status_history_rows,
        }


def seed_demo_dataset(
    db: Session,
    *,
    reset: bool = False,
    dataset: DemoDataset = DEMO_DATASET,
) -> DemoSeedReport:
    try:
        if reset:
            _delete_demo_roots(db, dataset)
            db.flush()

        candidate = _upsert_candidate(db, dataset)
        jobs = [_upsert_job(db, job) for job in dataset.jobs]
        db.flush()

        _rebuild_candidate_dependencies(db, candidate)
        for job in jobs:
            _rebuild_job_dependencies(db, job)
        db.flush()

        applications = [
            _upsert_application(db, candidate, job, demo_job)
            for job, demo_job in zip(jobs, dataset.jobs, strict=True)
        ]
        db.flush()

        _rebuild_matches_embeddings_and_tailoring(db, candidate, jobs)
        db.commit()
        return _build_report(db, dataset, reset=reset)
    except Exception:
        db.rollback()
        raise


def _delete_demo_roots(db: Session, dataset: DemoDataset) -> None:
    application_keys = [_application_seed_key(job) for job in dataset.jobs]
    job_keys = [job.seed_key for job in dataset.jobs]
    candidate_keys = [dataset.candidate.seed_key]

    db.execute(
        delete(Application).where(
            or_(Application.is_demo.is_(True), Application.demo_seed_key.in_(application_keys)),
        ),
    )
    db.execute(
        delete(JobPosting).where(
            or_(JobPosting.is_demo.is_(True), JobPosting.demo_seed_key.in_(job_keys)),
        ),
    )
    db.execute(
        delete(CandidateProfile).where(
            or_(
                CandidateProfile.is_demo.is_(True),
                CandidateProfile.demo_seed_key.in_(candidate_keys),
            ),
        ),
    )


def _upsert_candidate(db: Session, dataset: DemoDataset) -> CandidateProfile:
    demo_candidate = dataset.candidate
    candidate = db.scalar(
        select(CandidateProfile).where(
            CandidateProfile.demo_seed_key == demo_candidate.seed_key,
        ),
    )
    if candidate is None:
        candidate = CandidateProfile(demo_seed_key=demo_candidate.seed_key)
        db.add(candidate)

    candidate.full_name = demo_candidate.full_name
    candidate.headline = demo_candidate.headline
    candidate.location = demo_candidate.location
    candidate.professional_summary = demo_candidate.professional_summary
    candidate.years_experience = demo_candidate.years_experience
    candidate.resume_text = demo_candidate.resume_text
    candidate.is_demo = True
    return candidate


def _upsert_job(db: Session, demo_job: DemoJob) -> JobPosting:
    job = db.scalar(select(JobPosting).where(JobPosting.demo_seed_key == demo_job.seed_key))
    if job is None:
        job = JobPosting(demo_seed_key=demo_job.seed_key)
        db.add(job)

    job.title = demo_job.title
    job.company = demo_job.company
    job.location = demo_job.location
    job.employment_type = demo_job.employment_type
    job.work_mode = demo_job.work_mode
    job.source_url = demo_job.source_url
    job.description = demo_job.description
    job.is_demo = True
    return job


def _upsert_application(
    db: Session,
    candidate: CandidateProfile,
    job: JobPosting,
    demo_job: DemoJob,
) -> Application:
    seed_key = _application_seed_key(demo_job)
    application = db.scalar(select(Application).where(Application.demo_seed_key == seed_key))
    if application is None:
        application = Application(demo_seed_key=seed_key)
        db.add(application)

    application.candidate_id = candidate.id
    application.job_id = job.id
    application.status = demo_job.application_status
    application.notes = demo_job.application_notes
    application.is_demo = True
    application.applied_at = (
        SEED_TIMESTAMP - timedelta(days=8)
        if demo_job.application_status in {"applied", "interview", "rejected", "offer"}
        else None
    )
    application.next_follow_up_at = (
        SEED_TIMESTAMP + timedelta(days=3)
        if demo_job.application_status in {"saved", "interview", "offer"}
        else None
    )
    db.flush()
    _replace_status_history(db, application)
    return application


def _replace_status_history(db: Session, application: Application) -> None:
    db.execute(
        delete(ApplicationStatusHistory).where(
            ApplicationStatusHistory.application_id == application.id,
        ),
    )
    chain = _status_chain(application.status)
    previous_status: str | None = None
    for index, status in enumerate(chain):
        db.add(
            ApplicationStatusHistory(
                application_id=application.id,
                previous_status=previous_status,
                new_status=status,
                changed_at=SEED_TIMESTAMP - timedelta(days=len(chain) - index),
            ),
        )
        previous_status = status


def _status_chain(status: str) -> list[str]:
    chains = {
        "saved": ["saved"],
        "applied": ["saved", "applied"],
        "interview": ["saved", "applied", "interview"],
        "rejected": ["saved", "applied", "interview", "rejected"],
        "offer": ["saved", "applied", "interview", "offer"],
    }
    return chains[status]


def _rebuild_candidate_dependencies(db: Session, candidate: CandidateProfile) -> None:
    parsed = parse_candidate_resume(candidate.resume_text or "")
    db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == candidate.id))
    db.execute(
        delete(CandidateParseResult).where(CandidateParseResult.candidate_id == candidate.id),
    )
    db.flush()

    skill_map = _get_or_create_skills(
        db,
        (skill.normalized_name for skill in parsed.skills),
    )
    for parsed_skill in parsed.skills:
        skill = skill_map[parsed_skill.normalized_name]
        db.add(
            CandidateSkill(
                candidate_id=candidate.id,
                skill_id=skill.id,
                evidence_text=parsed_skill.evidence_text,
                created_at=SEED_TIMESTAMP,
            ),
        )
    db.add(
        CandidateParseResult(
            candidate_id=candidate.id,
            parsed_years_experience=parsed.parsed_years_experience,
            education_level=parsed.education_level,
            parser_version=parsed.parser_version,
            parsed_at=SEED_TIMESTAMP,
        ),
    )


def _rebuild_job_dependencies(db: Session, job: JobPosting) -> None:
    parsed = parse_job_description(job.description)
    db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
    db.execute(delete(JobParseResult).where(JobParseResult.job_id == job.id))
    db.flush()

    parsed_skills = parsed.required_skills + parsed.preferred_skills
    skill_map = _get_or_create_skills(
        db,
        (skill.normalized_name for skill in parsed_skills),
    )
    for parsed_skill in parsed_skills:
        skill = skill_map[parsed_skill.normalized_name]
        db.add(
            JobSkill(
                job_id=job.id,
                skill_id=skill.id,
                requirement_type=parsed_skill.requirement_type,
                evidence_text=parsed_skill.evidence_text,
                created_at=SEED_TIMESTAMP,
            ),
        )
    db.add(
        JobParseResult(
            job_id=job.id,
            minimum_years_experience=parsed.minimum_years_experience,
            education_requirement=parsed.education_requirement,
            parser_version=parsed.parser_version,
            parsed_at=SEED_TIMESTAMP,
        ),
    )


def _get_or_create_skills(
    db: Session,
    normalized_names: Iterable[str],
) -> dict[str, Skill]:
    names = sorted(set(normalized_names))
    if not names:
        return {}

    existing = db.scalars(select(Skill).where(Skill.normalized_name.in_(names))).all()
    skill_map = {skill.normalized_name: skill for skill in existing}
    for normalized_name in names:
        if normalized_name in skill_map:
            continue
        display_name = _display_skill_name(normalized_name)
        skill = Skill(
            name=display_name,
            normalized_name=normalized_name,
            created_at=SEED_TIMESTAMP,
        )
        db.add(skill)
        skill_map[normalized_name] = skill
    db.flush()
    return skill_map


def _display_skill_name(normalized_name: str) -> str:
    from backend.services.skill_catalog import find_catalog_entry

    entry = find_catalog_entry(normalized_name)
    return entry.name if entry is not None else normalized_name.replace("_", " ").title()


def _rebuild_matches_embeddings_and_tailoring(
    db: Session,
    candidate: CandidateProfile,
    jobs: list[JobPosting],
) -> None:
    candidate_embedding = _upsert_candidate_embedding(db, candidate)
    for job in jobs:
        job_embedding = _upsert_job_embedding(db, job)
        score_result = _replace_match_result(db, candidate, job)
        _upsert_semantic_result(db, candidate, job, candidate_embedding, job_embedding)
        _upsert_tailoring_result(db, candidate, job, score_result)


def _upsert_candidate_embedding(
    db: Session,
    candidate: CandidateProfile,
) -> CandidateEmbedding:
    source_text = build_candidate_embedding_source(
        headline=candidate.headline,
        professional_summary=candidate.professional_summary,
        resume_text=candidate.resume_text,
    )
    embedding = db.scalar(
        select(CandidateEmbedding).where(CandidateEmbedding.candidate_id == candidate.id),
    )
    if embedding is None:
        embedding = CandidateEmbedding(candidate_id=candidate.id)
        db.add(embedding)
    embedding.model_name = DEMO_EMBEDDING_MODEL
    embedding.dimensions = EMBEDDING_DIMENSIONS
    embedding.source_hash = embedding_source_hash(source_text)
    embedding.embedding = _deterministic_vector(source_text)
    embedding.embedded_at = SEED_TIMESTAMP
    return embedding


def _upsert_job_embedding(db: Session, job: JobPosting) -> JobEmbedding:
    source_text = build_job_embedding_source(
        title=job.title,
        company=job.company,
        description=job.description,
    )
    embedding = db.scalar(select(JobEmbedding).where(JobEmbedding.job_id == job.id))
    if embedding is None:
        embedding = JobEmbedding(job_id=job.id)
        db.add(embedding)
    embedding.model_name = DEMO_EMBEDDING_MODEL
    embedding.dimensions = EMBEDDING_DIMENSIONS
    embedding.source_hash = embedding_source_hash(source_text)
    embedding.embedding = _deterministic_vector(source_text)
    embedding.embedded_at = SEED_TIMESTAMP
    return embedding


def _replace_match_result(
    db: Session,
    candidate: CandidateProfile,
    job: JobPosting,
) -> MatchScoreResult:
    existing = db.scalar(
        select(MatchResult).where(
            MatchResult.candidate_id == candidate.id,
            MatchResult.job_id == job.id,
        ),
    )
    if existing is not None:
        db.execute(
            delete(MatchSkillDetail).where(MatchSkillDetail.match_result_id == existing.id),
        )
        db.delete(existing)
        db.flush()

    score_result = calculate_match_score(
        _candidate_match_input(db, candidate.id),
        _job_match_input(db, job.id),
    )
    match_result = MatchResult(
        candidate_id=candidate.id,
        job_id=job.id,
        overall_score=score_result.overall_score,
        required_skill_score=score_result.required_skill_score,
        preferred_skill_score=score_result.preferred_skill_score,
        experience_score=score_result.experience_score,
        education_score=score_result.education_score,
        matched_required_count=score_result.matched_required_count,
        total_required_count=score_result.total_required_count,
        matched_preferred_count=score_result.matched_preferred_count,
        total_preferred_count=score_result.total_preferred_count,
        candidate_years_used=score_result.candidate_years_used,
        required_years=score_result.required_years,
        candidate_education_level=score_result.candidate_education_level,
        required_education_level=score_result.required_education_level,
        scoring_version=score_result.scoring_version,
        calculated_at=SEED_TIMESTAMP,
    )
    db.add(match_result)
    db.flush()

    for detail in score_result.skill_details:
        if detail.skill_id is None:
            continue
        db.add(
            MatchSkillDetail(
                match_result_id=match_result.id,
                skill_id=detail.skill_id,
                requirement_type=detail.requirement_type,
                matched=detail.matched,
                created_at=SEED_TIMESTAMP,
            ),
        )
    return score_result


def _candidate_match_input(db: Session, candidate_id: int) -> CandidateMatchInput:
    parse_result = db.scalar(
        select(CandidateParseResult).where(
            CandidateParseResult.candidate_id == candidate_id,
        ),
    )
    candidate = db.get(CandidateProfile, candidate_id)
    skill_rows = db.execute(
        select(CandidateSkill, Skill)
        .join(Skill, CandidateSkill.skill_id == Skill.id)
        .where(CandidateSkill.candidate_id == candidate_id)
        .order_by(Skill.normalized_name, Skill.name),
    ).all()
    return CandidateMatchInput(
        skills=tuple(
            MatchSkillInput(skill.id, skill.name, skill.normalized_name)
            for _, skill in skill_rows
        ),
        parsed_years_experience=parse_result.parsed_years_experience if parse_result else None,
        profile_years_experience=candidate.years_experience if candidate else None,
        education_level=parse_result.education_level if parse_result else None,
    )


def _job_match_input(db: Session, job_id: int) -> JobMatchInput:
    parse_result = db.scalar(select(JobParseResult).where(JobParseResult.job_id == job_id))
    skill_rows = db.execute(
        select(JobSkill, Skill)
        .join(Skill, JobSkill.skill_id == Skill.id)
        .where(JobSkill.job_id == job_id)
        .order_by(JobSkill.requirement_type, Skill.normalized_name, Skill.name),
    ).all()
    required: list[MatchSkillInput] = []
    preferred: list[MatchSkillInput] = []
    for job_skill, skill in skill_rows:
        item = MatchSkillInput(skill.id, skill.name, skill.normalized_name)
        if job_skill.requirement_type == "required":
            required.append(item)
        else:
            preferred.append(item)
    return JobMatchInput(
        required_skills=tuple(required),
        preferred_skills=tuple(preferred),
        minimum_years_experience=(
            parse_result.minimum_years_experience if parse_result else None
        ),
        education_requirement=parse_result.education_requirement if parse_result else None,
    )


def _upsert_semantic_result(
    db: Session,
    candidate: CandidateProfile,
    job: JobPosting,
    candidate_embedding: CandidateEmbedding,
    job_embedding: JobEmbedding,
) -> SemanticMatchResult:
    result = db.scalar(
        select(SemanticMatchResult).where(
            SemanticMatchResult.candidate_id == candidate.id,
            SemanticMatchResult.job_id == job.id,
        ),
    )
    if result is None:
        result = SemanticMatchResult(candidate_id=candidate.id, job_id=job.id)
        db.add(result)
    similarity = cosine_similarity(candidate_embedding.embedding, job_embedding.embedding)
    result.cosine_similarity = Decimal(str(similarity))
    result.semantic_score = semantic_score_from_similarity(similarity)
    result.model_name = DEMO_EMBEDDING_MODEL
    result.candidate_source_hash = candidate_embedding.source_hash
    result.job_source_hash = job_embedding.source_hash
    result.calculated_at = SEED_TIMESTAMP
    return result


def _upsert_tailoring_result(
    db: Session,
    candidate: CandidateProfile,
    job: JobPosting,
    score_result: MatchScoreResult,
) -> TailoringResult:
    candidate_parse_result = db.scalar(
        select(CandidateParseResult).where(
            CandidateParseResult.candidate_id == candidate.id,
        ),
    )
    job_parse_result = db.scalar(select(JobParseResult).where(JobParseResult.job_id == job.id))
    candidate_skills = _candidate_skill_pairs(db, candidate.id)
    required_skills, preferred_skills = _job_skill_pairs(db, job.id)
    candidate_source = build_candidate_source(candidate, candidate_skills, candidate_parse_result)
    job_source = build_job_source(job, required_skills, preferred_skills, job_parse_result)
    match_context = build_match_context(score_result)
    sources = build_sources(
        candidate_source=candidate_source,
        job_source=job_source,
        match_context=match_context,
    )
    output = validate_tailoring_output(
        _tailoring_payload(job),
        resume_text=candidate.resume_text or "",
        gap_warnings=deterministic_gap_warnings(score_result),
    )
    result = db.scalar(
        select(TailoringResult).where(
            TailoringResult.candidate_id == candidate.id,
            TailoringResult.job_id == job.id,
        ),
    )
    if result is None:
        result = TailoringResult(candidate_id=candidate.id, job_id=job.id)
        db.add(result)
    result.model_name = DEMO_TAILORING_MODEL
    result.prompt_version = PROMPT_VERSION
    result.candidate_source_hash = sources.candidate_source_hash
    result.job_source_hash = sources.job_source_hash
    result.match_context_hash = sources.match_context_hash
    result.tailored_summary = output.tailored_summary
    result.resume_bullets = [
        {
            "text": bullet.text,
            "supporting_evidence": bullet.supporting_evidence,
            "keywords": bullet.keywords,
        }
        for bullet in output.resume_bullets
    ]
    result.cover_letter = output.cover_letter
    result.keywords_used = output.keywords_used
    result.warnings = output.warnings
    result.generated_at = SEED_TIMESTAMP
    return result


def _candidate_skill_pairs(db: Session, candidate_id: int) -> list[tuple[str, str]]:
    rows = db.execute(
        select(Skill.normalized_name, Skill.name)
        .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
        .where(CandidateSkill.candidate_id == candidate_id)
        .order_by(Skill.normalized_name, Skill.name),
    ).all()
    return [(row.normalized_name, row.name) for row in rows]


def _job_skill_pairs(
    db: Session,
    job_id: int,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    rows = db.execute(
        select(JobSkill.requirement_type, Skill.normalized_name, Skill.name)
        .join(Skill, JobSkill.skill_id == Skill.id)
        .where(JobSkill.job_id == job_id)
        .order_by(JobSkill.requirement_type, Skill.normalized_name, Skill.name),
    ).all()
    required: list[tuple[str, str]] = []
    preferred: list[tuple[str, str]] = []
    for row in rows:
        target = required if row.requirement_type == "required" else preferred
        target.append((row.normalized_name, row.name))
    return required, preferred


def _tailoring_payload(job: JobPosting) -> dict[str, object]:
    return {
        "tailored_summary": (
            f"Mira Quill can position her fictional Python, SQL, FastAPI, and "
            f"documentation experience toward the {job.title} role while keeping all "
            "claims grounded in the demo resume."
        ),
        "resume_bullets": [
            {
                "text": "Built Python dashboards with SQL and Power BI for fictional reporting teams.",
                "supporting_evidence": "Built Python dashboards with SQL and Power BI",
                "keywords": ["Python", "SQL", "Power BI"],
            },
            {
                "text": "Created FastAPI services with PostgreSQL and Docker for a fictional data project.",
                "supporting_evidence": "Created FastAPI services with PostgreSQL and Docker",
                "keywords": ["FastAPI", "PostgreSQL", "Docker"],
            },
            {
                "text": "Documented REST APIs and GitHub review notes for fictional product partners.",
                "supporting_evidence": "Documented REST APIs and GitHub review notes",
                "keywords": ["REST APIs", "GitHub", "Documentation"],
            },
        ],
        "cover_letter": (
            "Dear Hiring Manager,\n\n"
            f"I am excited about the fictional {job.title} opportunity at {job.company}. "
            "My demo resume shows Python dashboard work with SQL and Power BI, FastAPI "
            "services with PostgreSQL and Docker, and REST API documentation with GitHub "
            "review practices. I would focus on clear, truthful communication and "
            "well-documented data workflows for this role.\n\n"
            "Sincerely,\nMira Quill"
        ),
        "keywords_used": ["Docker", "FastAPI", "GitHub", "PostgreSQL", "Python", "SQL"],
        "warnings": ["Precomputed fictional demo output; not generated by a live model."],
    }


def _deterministic_vector(source_text: str) -> list[float]:
    digest = hashlib.sha256(source_text.encode("utf-8")).digest()
    values = [
        int.from_bytes(digest[index : index + 4], "big") / 1_000_000_000
        for index in range(0, EMBEDDING_DIMENSIONS * 4, 4)
    ]
    return [value if value > 0 else 0.1 for value in values]


def _application_seed_key(job: DemoJob) -> str:
    return job.seed_key.replace(":job:", ":application:")


def _build_report(
    db: Session,
    dataset: DemoDataset,
    *,
    reset: bool,
) -> DemoSeedReport:
    candidate_keys = [dataset.candidate.seed_key]
    job_keys = [job.seed_key for job in dataset.jobs]
    application_keys = [_application_seed_key(job) for job in dataset.jobs]
    candidate_ids = list(
        db.scalars(
            select(CandidateProfile.id).where(
                CandidateProfile.demo_seed_key.in_(candidate_keys),
            ),
        ),
    )
    job_ids = list(
        db.scalars(select(JobPosting.id).where(JobPosting.demo_seed_key.in_(job_keys))),
    )
    application_ids = list(
        db.scalars(
            select(Application.id).where(Application.demo_seed_key.in_(application_keys)),
        ),
    )
    return DemoSeedReport(
        seed_version=DEMO_SEED_VERSION,
        reset=reset,
        candidates=_count(db, CandidateProfile.id, CandidateProfile.id.in_(candidate_ids)),
        jobs=_count(db, JobPosting.id, JobPosting.id.in_(job_ids)),
        applications=_count(db, Application.id, Application.id.in_(application_ids)),
        candidate_parse_results=_count(
            db,
            CandidateParseResult.id,
            CandidateParseResult.candidate_id.in_(candidate_ids),
        ),
        job_parse_results=_count(db, JobParseResult.id, JobParseResult.job_id.in_(job_ids)),
        candidate_skills=_count(db, CandidateSkill.id, CandidateSkill.candidate_id.in_(candidate_ids)),
        job_skills=_count(db, JobSkill.id, JobSkill.job_id.in_(job_ids)),
        match_results=_count(
            db,
            MatchResult.id,
            MatchResult.candidate_id.in_(candidate_ids),
        ),
        semantic_match_results=_count(
            db,
            SemanticMatchResult.id,
            SemanticMatchResult.candidate_id.in_(candidate_ids),
        ),
        tailoring_results=_count(
            db,
            TailoringResult.id,
            TailoringResult.candidate_id.in_(candidate_ids),
        ),
        candidate_embeddings=_count(
            db,
            CandidateEmbedding.id,
            CandidateEmbedding.candidate_id.in_(candidate_ids),
        ),
        job_embeddings=_count(db, JobEmbedding.id, JobEmbedding.job_id.in_(job_ids)),
        status_history_rows=_count(
            db,
            ApplicationStatusHistory.id,
            ApplicationStatusHistory.application_id.in_(application_ids),
        ),
    )


def _count(db: Session, column, criterion) -> int:
    return db.scalar(select(func.count(column)).where(criterion)) or 0
