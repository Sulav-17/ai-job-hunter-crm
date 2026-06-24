from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models.candidate import CandidateProfile
from backend.models.candidate_parse_result import CandidateParseResult, CandidateSkill
from backend.models.job import JobPosting
from backend.models.job_parse_result import JobParseResult
from backend.models.skill import JobSkill, Skill
from backend.models.tailoring import TailoringResult
from backend.schemas.tailoring import TailoringGenerateRequest, TailoringResultResponse
from backend.services.generation_provider import (
    GenerationProvider,
    GenerationProviderError,
    MalformedGenerationOutputError,
)
from backend.services.match_scorer import (
    CandidateMatchInput,
    JobMatchInput,
    MatchScoreResult,
    MatchSkillInput,
    calculate_match_score,
)
from backend.services.tailoring_prompt import (
    PROMPT_VERSION,
    TailoringOutputError,
    TailoringSources,
    build_candidate_source,
    build_generation_prompt,
    build_job_source,
    build_match_context,
    build_sources,
    deterministic_gap_warnings,
    validate_tailoring_output,
)


class CandidateNotFoundError(ValueError):
    pass


class JobNotFoundError(ValueError):
    pass


class CandidateResumeTextRequiredError(ValueError):
    pass


class CandidateUnparsedError(ValueError):
    pass


class JobUnparsedError(ValueError):
    pass


class TailoringResultNotFoundError(ValueError):
    pass


class GenerationProviderUnavailableError(RuntimeError):
    pass


class GenerationProviderInvalidOutputError(RuntimeError):
    pass


def generate_tailoring_result(
    db: Session,
    candidate_id: int,
    job_id: int,
    request: TailoringGenerateRequest,
    provider: GenerationProvider,
) -> TailoringResultResponse:
    candidate = _get_candidate_or_raise(db, candidate_id)
    job = _get_job_or_raise(db, job_id)
    resume_text = _candidate_resume_text_or_raise(candidate)
    candidate_parse_result = _get_candidate_parse_result_or_raise(db, candidate.id)
    job_parse_result = _get_job_parse_result_or_raise(db, job.id)

    sources, score_result = _current_sources(
        db,
        candidate,
        job,
        candidate_parse_result,
        job_parse_result,
    )
    current_result = _get_tailoring_result(db, candidate.id, job.id)

    if (
        current_result is not None
        and not request.regenerate
        and _result_is_current(current_result, provider.model_identity, sources)
    ):
        return _response(current_result, stale=False)

    prompt = build_generation_prompt(sources)
    try:
        generated_payload = provider.generate(prompt)
    except GenerationProviderError as exc:
        raise GenerationProviderUnavailableError(
            "Generation provider unavailable",
        ) from exc
    except MalformedGenerationOutputError as exc:
        raise GenerationProviderInvalidOutputError(
            "Generation provider returned invalid output",
        ) from exc

    try:
        output = validate_tailoring_output(
            generated_payload,
            resume_text=resume_text,
            gap_warnings=deterministic_gap_warnings(score_result),
        )
    except TailoringOutputError as exc:
        raise GenerationProviderInvalidOutputError(
            "Generation provider returned invalid output",
        ) from exc

    try:
        if current_result is None:
            current_result = TailoringResult(candidate_id=candidate.id, job_id=job.id)
            db.add(current_result)

        _copy_output_to_result(
            current_result,
            provider_identity=provider.model_identity,
            sources=sources,
            output=output,
        )
        current_result.generated_at = func.now()
        db.commit()
        db.refresh(current_result)
    except SQLAlchemyError:
        db.rollback()
        raise

    return _response(current_result, stale=False)


def get_tailoring_result(
    db: Session,
    candidate_id: int,
    job_id: int,
    provider: GenerationProvider,
) -> TailoringResultResponse:
    candidate = _get_candidate_or_raise(db, candidate_id)
    job = _get_job_or_raise(db, job_id)
    result = _get_tailoring_result(db, candidate.id, job.id)
    if result is None:
        raise TailoringResultNotFoundError("Tailoring result not found")

    stale = True
    try:
        candidate_parse_result = _get_candidate_parse_result_or_raise(db, candidate.id)
        job_parse_result = _get_job_parse_result_or_raise(db, job.id)
        sources, _ = _current_sources(
            db,
            candidate,
            job,
            candidate_parse_result,
            job_parse_result,
        )
        stale = not _result_is_current(result, provider.model_identity, sources)
    except (
        CandidateResumeTextRequiredError,
        CandidateUnparsedError,
        JobUnparsedError,
    ):
        stale = True

    return _response(result, stale=stale)


def _get_candidate_or_raise(db: Session, candidate_id: int) -> CandidateProfile:
    candidate = db.get(CandidateProfile, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError("Candidate not found")
    return candidate


def _get_job_or_raise(db: Session, job_id: int) -> JobPosting:
    job = db.get(JobPosting, job_id)
    if job is None:
        raise JobNotFoundError("Job not found")
    return job


def _get_candidate_parse_result_or_raise(
    db: Session,
    candidate_id: int,
) -> CandidateParseResult:
    parse_result = db.scalar(
        select(CandidateParseResult).where(
            CandidateParseResult.candidate_id == candidate_id,
        ),
    )
    if parse_result is None:
        raise CandidateUnparsedError("Candidate must be parsed before tailoring")
    return parse_result


def _get_job_parse_result_or_raise(db: Session, job_id: int) -> JobParseResult:
    parse_result = db.scalar(
        select(JobParseResult).where(JobParseResult.job_id == job_id),
    )
    if parse_result is None:
        raise JobUnparsedError("Job must be parsed before tailoring")
    return parse_result


def _candidate_resume_text_or_raise(candidate: CandidateProfile) -> str:
    resume_text = candidate.resume_text or ""
    if resume_text.strip() == "":
        raise CandidateResumeTextRequiredError("Candidate resume text is required")
    return resume_text


def _get_tailoring_result(
    db: Session,
    candidate_id: int,
    job_id: int,
) -> TailoringResult | None:
    return db.scalar(
        select(TailoringResult).where(
            TailoringResult.candidate_id == candidate_id,
            TailoringResult.job_id == job_id,
        ),
    )


def _current_sources(
    db: Session,
    candidate: CandidateProfile,
    job: JobPosting,
    candidate_parse_result: CandidateParseResult,
    job_parse_result: JobParseResult,
) -> tuple[TailoringSources, MatchScoreResult]:
    _candidate_resume_text_or_raise(candidate)
    candidate_skills = _candidate_skill_pairs(db, candidate.id)
    required_skills, preferred_skills = _job_skill_pairs(db, job.id)
    candidate_source = build_candidate_source(
        candidate,
        candidate_skills,
        candidate_parse_result,
    )
    job_source = build_job_source(
        job,
        required_skills,
        preferred_skills,
        job_parse_result,
    )
    score_result = calculate_match_score(
        _build_candidate_input(candidate, candidate_parse_result, candidate_skills),
        _build_job_input(job_parse_result, required_skills, preferred_skills),
    )
    match_context = build_match_context(score_result)
    return (
        build_sources(
            candidate_source=candidate_source,
            job_source=job_source,
            match_context=match_context,
        ),
        score_result,
    )


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
        skill_pair = (row.normalized_name, row.name)
        if row.requirement_type == "required":
            required.append(skill_pair)
        else:
            preferred.append(skill_pair)
    return required, preferred


def _build_candidate_input(
    candidate: CandidateProfile,
    parse_result: CandidateParseResult,
    skill_pairs: list[tuple[str, str]],
) -> CandidateMatchInput:
    return CandidateMatchInput(
        skills=tuple(
            MatchSkillInput(None, canonical_name, normalized_name)
            for normalized_name, canonical_name in skill_pairs
        ),
        parsed_years_experience=parse_result.parsed_years_experience,
        profile_years_experience=candidate.years_experience,
        education_level=parse_result.education_level,
    )


def _build_job_input(
    parse_result: JobParseResult,
    required_skill_pairs: list[tuple[str, str]],
    preferred_skill_pairs: list[tuple[str, str]],
) -> JobMatchInput:
    return JobMatchInput(
        required_skills=tuple(
            MatchSkillInput(None, canonical_name, normalized_name)
            for normalized_name, canonical_name in required_skill_pairs
        ),
        preferred_skills=tuple(
            MatchSkillInput(None, canonical_name, normalized_name)
            for normalized_name, canonical_name in preferred_skill_pairs
        ),
        minimum_years_experience=parse_result.minimum_years_experience,
        education_requirement=parse_result.education_requirement,
    )


def _result_is_current(
    result: TailoringResult,
    provider_identity: str,
    sources: TailoringSources,
) -> bool:
    return (
        result.model_name == provider_identity
        and result.prompt_version == PROMPT_VERSION
        and result.candidate_source_hash == sources.candidate_source_hash
        and result.job_source_hash == sources.job_source_hash
        and result.match_context_hash == sources.match_context_hash
    )


def _copy_output_to_result(
    result: TailoringResult,
    *,
    provider_identity: str,
    sources: TailoringSources,
    output,
) -> None:
    result.model_name = provider_identity
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


def _response(result: TailoringResult, *, stale: bool) -> TailoringResultResponse:
    return TailoringResultResponse(
        candidate_id=result.candidate_id,
        job_id=result.job_id,
        model_name=result.model_name,
        prompt_version=result.prompt_version,
        candidate_source_hash=result.candidate_source_hash,
        job_source_hash=result.job_source_hash,
        match_context_hash=result.match_context_hash,
        tailored_summary=result.tailored_summary,
        resume_bullets=result.resume_bullets,
        cover_letter=result.cover_letter,
        keywords_used=result.keywords_used,
        warnings=result.warnings,
        generated_at=result.generated_at,
        stale=stale,
    )
