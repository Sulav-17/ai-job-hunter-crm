from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CandidateBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    headline: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=120)
    professional_summary: str | None = Field(default=None, max_length=5000)
    years_experience: int | None = Field(default=None, ge=0, le=80)
    resume_text: str | None = Field(default=None, max_length=50000)


class CandidateCreate(CandidateBase):
    full_name: str = Field(min_length=1, max_length=120)


class CandidateUpdate(CandidateBase):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def reject_empty_update(self) -> "CandidateUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class CandidateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    headline: str | None
    location: str | None
    years_experience: int | None
    created_at: datetime
    updated_at: datetime


class CandidateDetail(CandidateSummary):
    professional_summary: str | None
    resume_text: str | None
