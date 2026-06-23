from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models.job import JobPosting
from backend.models.job_parse_result import JobParseResult
from backend.models.skill import JobSkill, Skill
from backend.schemas.job_parser import JobParseResultResponse, ParsedSkill
from backend.services.job_parser import ParsedJob, parse_job_description


def parse_and_persist_job(db: Session, job_id: int) -> JobParseResultResponse | None:
    job = db.get(JobPosting, job_id)
    if job is None:
        return None

    parsed_job = parse_job_description(job.description)

    try:
        db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
        skills_by_normalized_name = _get_or_create_skills(db, parsed_job)

        for parsed_skill in parsed_job.required_skills + parsed_job.preferred_skills:
            skill = skills_by_normalized_name[parsed_skill.normalized_name]
            db.add(
                JobSkill(
                    job_id=job.id,
                    skill_id=skill.id,
                    requirement_type=parsed_skill.requirement_type,
                    evidence_text=parsed_skill.evidence_text,
                ),
            )

        parse_result = db.scalar(
            select(JobParseResult).where(JobParseResult.job_id == job.id),
        )
        if parse_result is None:
            parse_result = JobParseResult(
                job_id=job.id,
                minimum_years_experience=parsed_job.minimum_years_experience,
                education_requirement=parsed_job.education_requirement,
                parser_version=parsed_job.parser_version,
            )
            db.add(parse_result)
        else:
            parse_result.minimum_years_experience = parsed_job.minimum_years_experience
            parse_result.education_requirement = parsed_job.education_requirement
            parse_result.parser_version = parsed_job.parser_version
            parse_result.parsed_at = func.now()

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return get_parse_result(db, job.id)


def get_parse_result(db: Session, job_id: int) -> JobParseResultResponse | None:
    parse_result = db.scalar(
        select(JobParseResult).where(JobParseResult.job_id == job_id),
    )
    if parse_result is None:
        return None

    skill_rows = db.execute(
        select(JobSkill, Skill)
        .join(Skill, JobSkill.skill_id == Skill.id)
        .where(JobSkill.job_id == job_id)
        .order_by(JobSkill.requirement_type, Skill.normalized_name, Skill.name),
    ).all()

    required_skills: list[ParsedSkill] = []
    preferred_skills: list[ParsedSkill] = []
    for job_skill, skill in skill_rows:
        parsed_skill = ParsedSkill(
            skill_id=skill.id,
            name=skill.name,
            normalized_name=skill.normalized_name,
            requirement_type=job_skill.requirement_type,
            evidence_text=job_skill.evidence_text,
        )
        if job_skill.requirement_type == "required":
            required_skills.append(parsed_skill)
        else:
            preferred_skills.append(parsed_skill)

    return JobParseResultResponse(
        job_id=job_id,
        parser_version=parse_result.parser_version,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        minimum_years_experience=parse_result.minimum_years_experience,
        education_requirement=parse_result.education_requirement,
        parsed_at=parse_result.parsed_at,
    )


def _get_or_create_skills(db: Session, parsed_job: ParsedJob) -> dict[str, Skill]:
    parsed_skills = parsed_job.required_skills + parsed_job.preferred_skills
    normalized_names = sorted({skill.normalized_name for skill in parsed_skills})
    if not normalized_names:
        return {}

    existing_skills = db.scalars(
        select(Skill).where(Skill.normalized_name.in_(normalized_names)),
    ).all()
    skills_by_normalized_name = {
        skill.normalized_name: skill for skill in existing_skills
    }

    for parsed_skill in sorted(
        parsed_skills,
        key=lambda skill: (skill.normalized_name, skill.name),
    ):
        if parsed_skill.normalized_name not in skills_by_normalized_name:
            skill = Skill(
                name=parsed_skill.name,
                normalized_name=parsed_skill.normalized_name,
            )
            db.add(skill)
            skills_by_normalized_name[skill.normalized_name] = skill

    db.flush()
    return skills_by_normalized_name
