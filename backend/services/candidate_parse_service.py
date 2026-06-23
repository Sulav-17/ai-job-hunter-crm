from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models.candidate import CandidateProfile
from backend.models.candidate_parse_result import CandidateParseResult, CandidateSkill
from backend.models.skill import Skill
from backend.schemas.candidate_parser import (
    CandidateParsedSkill,
    CandidateParseResultResponse,
)
from backend.services.candidate_parser import ParsedCandidate, parse_candidate_resume


class MissingResumeTextError(ValueError):
    pass


def parse_and_persist_candidate(
    db: Session,
    candidate_id: int,
) -> CandidateParseResultResponse | None:
    candidate = db.get(CandidateProfile, candidate_id)
    if candidate is None:
        return None

    if candidate.resume_text is None or candidate.resume_text.strip() == "":
        raise MissingResumeTextError("Candidate resume text is required")

    parsed_candidate = parse_candidate_resume(candidate.resume_text)

    try:
        db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == candidate.id))
        skills_by_normalized_name = _get_or_create_skills(db, parsed_candidate)

        for parsed_skill in parsed_candidate.skills:
            skill = skills_by_normalized_name[parsed_skill.normalized_name]
            db.add(
                CandidateSkill(
                    candidate_id=candidate.id,
                    skill_id=skill.id,
                    evidence_text=parsed_skill.evidence_text,
                ),
            )

        parse_result = db.scalar(
            select(CandidateParseResult).where(
                CandidateParseResult.candidate_id == candidate.id,
            ),
        )
        if parse_result is None:
            parse_result = CandidateParseResult(
                candidate_id=candidate.id,
                parsed_years_experience=parsed_candidate.parsed_years_experience,
                education_level=parsed_candidate.education_level,
                parser_version=parsed_candidate.parser_version,
            )
            db.add(parse_result)
        else:
            parse_result.parsed_years_experience = (
                parsed_candidate.parsed_years_experience
            )
            parse_result.education_level = parsed_candidate.education_level
            parse_result.parser_version = parsed_candidate.parser_version
            parse_result.parsed_at = func.now()

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return get_parse_result(db, candidate.id)


def get_parse_result(
    db: Session,
    candidate_id: int,
) -> CandidateParseResultResponse | None:
    parse_result = db.scalar(
        select(CandidateParseResult).where(
            CandidateParseResult.candidate_id == candidate_id,
        ),
    )
    if parse_result is None:
        return None

    skill_rows = db.execute(
        select(CandidateSkill, Skill)
        .join(Skill, CandidateSkill.skill_id == Skill.id)
        .where(CandidateSkill.candidate_id == candidate_id)
        .order_by(Skill.normalized_name, Skill.name),
    ).all()

    skills = [
        CandidateParsedSkill(
            skill_id=skill.id,
            name=skill.name,
            normalized_name=skill.normalized_name,
            evidence_text=candidate_skill.evidence_text,
        )
        for candidate_skill, skill in skill_rows
    ]

    return CandidateParseResultResponse(
        candidate_id=candidate_id,
        parser_version=parse_result.parser_version,
        parsed_years_experience=parse_result.parsed_years_experience,
        education_level=parse_result.education_level,
        parsed_at=parse_result.parsed_at,
        skills=skills,
    )


def _get_or_create_skills(
    db: Session,
    parsed_candidate: ParsedCandidate,
) -> dict[str, Skill]:
    normalized_names = sorted(
        {skill.normalized_name for skill in parsed_candidate.skills},
    )
    if not normalized_names:
        return {}

    existing_skills = db.scalars(
        select(Skill).where(Skill.normalized_name.in_(normalized_names)),
    ).all()
    skills_by_normalized_name = {
        skill.normalized_name: skill for skill in existing_skills
    }

    for parsed_skill in parsed_candidate.skills:
        if parsed_skill.normalized_name not in skills_by_normalized_name:
            skill = Skill(
                name=parsed_skill.name,
                normalized_name=parsed_skill.normalized_name,
            )
            db.add(skill)
            skills_by_normalized_name[skill.normalized_name] = skill

    db.flush()
    return skills_by_normalized_name
