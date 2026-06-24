from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TailoringGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regenerate: bool = False


class ResumeBulletResponse(BaseModel):
    text: str
    supporting_evidence: str
    keywords: list[str]


class TailoringResultResponse(BaseModel):
    candidate_id: int
    job_id: int
    model_name: str
    prompt_version: str
    candidate_source_hash: str = Field(min_length=64, max_length=64)
    job_source_hash: str = Field(min_length=64, max_length=64)
    match_context_hash: str = Field(min_length=64, max_length=64)
    tailored_summary: str
    resume_bullets: list[ResumeBulletResponse]
    cover_letter: str
    keywords_used: list[str]
    warnings: list[str]
    generated_at: datetime
    stale: bool
