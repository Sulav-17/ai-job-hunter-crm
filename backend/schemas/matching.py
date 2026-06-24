from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MatchApplicableWeights(BaseModel):
    required_skills: int | None
    preferred_skills: int | None
    experience: int | None
    education: int | None


class MatchSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: int
    name: str
    normalized_name: str
    requirement_type: str
    matched: bool


class MatchResultResponse(BaseModel):
    candidate_id: int
    job_id: int
    overall_score: int
    required_skill_score: int | None
    preferred_skill_score: int | None
    experience_score: int | None
    education_score: int | None
    applicable_weights: MatchApplicableWeights
    matched_required_count: int
    total_required_count: int
    matched_preferred_count: int
    total_preferred_count: int
    candidate_years_used: int | None
    required_years: int | None
    candidate_education_level: str | None
    required_education_level: str | None
    scoring_version: str
    calculated_at: datetime
    matched_required_skills: list[MatchSkillResponse]
    missing_required_skills: list[MatchSkillResponse]
    matched_preferred_skills: list[MatchSkillResponse]
    missing_preferred_skills: list[MatchSkillResponse]
