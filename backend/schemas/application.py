from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ApplicationStatus = Literal["saved", "applied", "interview", "rejected", "offer"]
DEFAULT_APPLICATION_STATUS: ApplicationStatus = "saved"


class ApplicationBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    applied_at: datetime | None = None
    next_follow_up_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=5000)


class ApplicationCreate(ApplicationBase):
    candidate_id: int = Field(gt=0)
    job_id: int = Field(gt=0)
    status: ApplicationStatus = DEFAULT_APPLICATION_STATUS


class ApplicationUpdate(ApplicationBase):
    status: ApplicationStatus | None = None

    @model_validator(mode="after")
    def reject_empty_or_null_status_update(self) -> "ApplicationUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("status cannot be null")

        return self


class ApplicationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    job_id: int
    status: str
    applied_at: datetime | None
    next_follow_up_at: datetime | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationSummary):
    notes: str | None


class ApplicationStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    previous_status: str | None
    new_status: str
    changed_at: datetime
