from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EmploymentType = Literal[
    "full_time",
    "part_time",
    "contract",
    "internship",
    "temporary",
    "other",
]
WorkMode = Literal["remote", "hybrid", "on_site"]


class JobBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    location: str | None = Field(default=None, max_length=160)
    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None
    source_url: str | None = Field(default=None, max_length=2048)

    @field_validator("location", "source_url", mode="before")
    @classmethod
    def blank_optional_text_to_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        parsed_url = urlparse(value)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
            raise ValueError("source_url must be an HTTP or HTTPS URL with a hostname")

        return value


class JobCreate(JobBase):
    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=50, max_length=50000)


class JobUpdate(JobBase):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    company: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=50, max_length=50000)

    @model_validator(mode="after")
    def reject_empty_or_null_required_update(self) -> "JobUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        for field_name in ("title", "company", "description"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")

        return self


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    location: str | None
    employment_type: str | None
    work_mode: str | None
    created_at: datetime
    updated_at: datetime


class JobDetail(JobSummary):
    source_url: str | None
    description: str
