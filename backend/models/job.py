from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.job_parse_result import JobParseResult
    from backend.models.skill import JobSkill


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(title)) > 0",
            name="ck_job_postings_title_not_blank",
        ),
        CheckConstraint(
            "length(btrim(company)) > 0",
            name="ck_job_postings_company_not_blank",
        ),
        CheckConstraint(
            "char_length(btrim(description)) >= 50",
            name="ck_job_postings_description_min_length",
        ),
        CheckConstraint(
            "employment_type IS NULL OR employment_type IN "
            "('full_time', 'part_time', 'contract', 'internship', "
            "'temporary', 'other')",
            name="ck_job_postings_employment_type",
        ),
        CheckConstraint(
            "work_mode IS NULL OR work_mode IN ('remote', 'hybrid', 'on_site')",
            name="ck_job_postings_work_mode",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    job_skills: Mapped[list[JobSkill]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    parse_result: Mapped[JobParseResult | None] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
