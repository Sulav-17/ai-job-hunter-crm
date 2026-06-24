from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models.candidate import CandidateProfile
from backend.models.candidate_parse_result import CandidateParseResult, CandidateSkill
from backend.models.job import JobPosting
from backend.models.job_parse_result import JobParseResult
from backend.models.match_result import MatchResult, MatchSkillDetail
from backend.models.skill import JobSkill, Skill
from backend.schemas.matching import (
    MatchApplicableWeights,
    MatchResultResponse,
    MatchSkillResponse,
)
from backend.services.match_scorer import (
    CandidateMatchInput,
    JobMatchInput,
    MatchScoreResult,
    MatchSkillInput,
    calculate_match_score,
)


class CandidateNotFoundError(ValueError):
    pass


class JobNotFoundError(ValueError):
    pass


class CandidateUnparsedError(ValueError):
    pass


class JobUnparsedError(ValueError):
    pass


class MatchResultNotFoundError(ValueError):
    pass


def calculate_and_persist_match(
    db: Session,
    candidate_id: int,
    job_id: int,
) -> MatchResultResponse:
    candidate = _get_candidate_or_raise(db, candidate_id)
    job = _get_job_or_raise(db, job_id)
    candidate_parse_result = _get_candidate_parse_result_or_raise(db, candidate.id)
    job_parse_result = _get_job_parse_result_or_raise(db, job.id)

    candidate_input = _build_candidate_input(db, candidate, candidate_parse_result)
    job_input = _build_job_input(db, job_parse_result)
    score_result = calculate_match_score(candidate_input, job_input)

    try:
        match_result = db.scalar(
            select(MatchResult).where(
                MatchResult.candidate_id == candidate.id,
                MatchResult.job_id == job.id,
            ),
        )
        if match_result is None:
            match_result = MatchResult(candidate_id=candidate.id, job_id=job.id)
            db.add(match_result)
        else:
            db.execute(
                delete(MatchSkillDetail).where(
                    MatchSkillDetail.match_result_id == match_result.id,
                ),
            )

        _copy_score_to_match_result(match_result, score_result)
        match_result.calculated_at = func.now()
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
                ),
            )

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return get_saved_match_result(db, candidate.id, job.id)


def get_saved_match_result(
    db: Session,
    candidate_id: int,
    job_id: int,
) -> MatchResultResponse:
    _get_candidate_or_raise(db, candidate_id)
    _get_job_or_raise(db, job_id)

    match_result = db.scalar(
        select(MatchResult).where(
            MatchResult.candidate_id == candidate_id,
            MatchResult.job_id == job_id,
        ),
    )
    if match_result is None:
        raise MatchResultNotFoundError("Match result not found")

    return _build_response(db, match_result)


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
        raise CandidateUnparsedError("Candidate must be parsed before matching")
    return parse_result


def _get_job_parse_result_or_raise(db: Session, job_id: int) -> JobParseResult:
    parse_result = db.scalar(
        select(JobParseResult).where(JobParseResult.job_id == job_id),
    )
    if parse_result is None:
        raise JobUnparsedError("Job must be parsed before matching")
    return parse_result


def _build_candidate_input(
    db: Session,
    candidate: CandidateProfile,
    parse_result: CandidateParseResult,
) -> CandidateMatchInput:
    skill_rows = db.execute(
        select(CandidateSkill, Skill)
        .join(Skill, CandidateSkill.skill_id == Skill.id)
        .where(CandidateSkill.candidate_id == candidate.id)
        .order_by(Skill.normalized_name, Skill.name),
    ).all()

    return CandidateMatchInput(
        skills=tuple(
            MatchSkillInput(
                skill_id=skill.id,
                name=skill.name,
                normalized_name=skill.normalized_name,
            )
            for _, skill in skill_rows
        ),
        parsed_years_experience=parse_result.parsed_years_experience,
        profile_years_experience=candidate.years_experience,
        education_level=parse_result.education_level,
    )


def _build_job_input(db: Session, parse_result: JobParseResult) -> JobMatchInput:
    skill_rows = db.execute(
        select(JobSkill, Skill)
        .join(Skill, JobSkill.skill_id == Skill.id)
        .where(JobSkill.job_id == parse_result.job_id)
        .order_by(Skill.normalized_name, Skill.name),
    ).all()
    required_skills: list[MatchSkillInput] = []
    preferred_skills: list[MatchSkillInput] = []

    for job_skill, skill in skill_rows:
        skill_input = MatchSkillInput(
            skill_id=skill.id,
            name=skill.name,
            normalized_name=skill.normalized_name,
        )
        if job_skill.requirement_type == "required":
            required_skills.append(skill_input)
        else:
            preferred_skills.append(skill_input)

    return JobMatchInput(
        required_skills=tuple(required_skills),
        preferred_skills=tuple(preferred_skills),
        minimum_years_experience=parse_result.minimum_years_experience,
        education_requirement=parse_result.education_requirement,
    )


def _copy_score_to_match_result(
    match_result: MatchResult,
    score_result: MatchScoreResult,
) -> None:
    match_result.overall_score = score_result.overall_score
    match_result.required_skill_score = score_result.required_skill_score
    match_result.preferred_skill_score = score_result.preferred_skill_score
    match_result.experience_score = score_result.experience_score
    match_result.education_score = score_result.education_score
    match_result.matched_required_count = score_result.matched_required_count
    match_result.total_required_count = score_result.total_required_count
    match_result.matched_preferred_count = score_result.matched_preferred_count
    match_result.total_preferred_count = score_result.total_preferred_count
    match_result.candidate_years_used = score_result.candidate_years_used
    match_result.required_years = score_result.required_years
    match_result.candidate_education_level = score_result.candidate_education_level
    match_result.required_education_level = score_result.required_education_level
    match_result.scoring_version = score_result.scoring_version


def _build_response(db: Session, match_result: MatchResult) -> MatchResultResponse:
    detail_rows = db.execute(
        select(MatchSkillDetail, Skill)
        .join(Skill, MatchSkillDetail.skill_id == Skill.id)
        .where(MatchSkillDetail.match_result_id == match_result.id)
        .order_by(Skill.normalized_name, Skill.name),
    ).all()

    matched_required_skills: list[MatchSkillResponse] = []
    missing_required_skills: list[MatchSkillResponse] = []
    matched_preferred_skills: list[MatchSkillResponse] = []
    missing_preferred_skills: list[MatchSkillResponse] = []

    for detail, skill in detail_rows:
        response_skill = MatchSkillResponse(
            skill_id=skill.id,
            name=skill.name,
            normalized_name=skill.normalized_name,
            requirement_type=detail.requirement_type,
            matched=detail.matched,
        )
        if detail.requirement_type == "required" and detail.matched:
            matched_required_skills.append(response_skill)
        elif detail.requirement_type == "required":
            missing_required_skills.append(response_skill)
        elif detail.matched:
            matched_preferred_skills.append(response_skill)
        else:
            missing_preferred_skills.append(response_skill)

    applicable_weights = _derive_applicable_weights(match_result)
    return MatchResultResponse(
        candidate_id=match_result.candidate_id,
        job_id=match_result.job_id,
        overall_score=match_result.overall_score,
        required_skill_score=match_result.required_skill_score,
        preferred_skill_score=match_result.preferred_skill_score,
        experience_score=match_result.experience_score,
        education_score=match_result.education_score,
        applicable_weights=applicable_weights,
        matched_required_count=match_result.matched_required_count,
        total_required_count=match_result.total_required_count,
        matched_preferred_count=match_result.matched_preferred_count,
        total_preferred_count=match_result.total_preferred_count,
        candidate_years_used=match_result.candidate_years_used,
        required_years=match_result.required_years,
        candidate_education_level=match_result.candidate_education_level,
        required_education_level=match_result.required_education_level,
        scoring_version=match_result.scoring_version,
        calculated_at=match_result.calculated_at,
        matched_required_skills=matched_required_skills,
        missing_required_skills=missing_required_skills,
        matched_preferred_skills=matched_preferred_skills,
        missing_preferred_skills=missing_preferred_skills,
    )


def _derive_applicable_weights(match_result: MatchResult) -> MatchApplicableWeights:
    score_result = calculate_match_score(
        CandidateMatchInput(
            skills=(),
            parsed_years_experience=match_result.candidate_years_used,
            profile_years_experience=None,
            education_level=match_result.candidate_education_level,
        ),
        JobMatchInput(
            required_skills=(
                (MatchSkillInput(None, "placeholder", "placeholder"),)
                if match_result.required_skill_score is not None
                else ()
            ),
            preferred_skills=(
                (MatchSkillInput(None, "placeholder", "placeholder"),)
                if match_result.preferred_skill_score is not None
                else ()
            ),
            minimum_years_experience=match_result.required_years,
            education_requirement=match_result.required_education_level,
        ),
    )
    return MatchApplicableWeights(
        required_skills=score_result.applicable_weights.required_skills,
        preferred_skills=score_result.applicable_weights.preferred_skills,
        experience=score_result.applicable_weights.experience,
        education=score_result.applicable_weights.education,
    )
