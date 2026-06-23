from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CandidateParsedSkill(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: int
    name: str
    normalized_name: str
    evidence_text: str | None


class CandidateParseResultResponse(BaseModel):
    candidate_id: int
    parser_version: str
    parsed_years_experience: int | None
    education_level: str | None
    parsed_at: datetime
    skills: list[CandidateParsedSkill]
