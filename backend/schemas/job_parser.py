from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ParsedSkill(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: int
    name: str
    normalized_name: str
    requirement_type: str
    evidence_text: str | None


class JobParseResultResponse(BaseModel):
    job_id: int
    parser_version: str
    required_skills: list[ParsedSkill]
    preferred_skills: list[ParsedSkill]
    minimum_years_experience: int | None
    education_requirement: str | None
    parsed_at: datetime
