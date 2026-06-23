from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.job import JobPosting


class JobParseResult(Base):
    __tablename__ = "job_parse_results"
    __table_args__ = (
        CheckConstraint(
            "minimum_years_experience IS NULL OR minimum_years_experience >= 0",
            name="ck_job_parse_results_minimum_years_non_negative",
        ),
        CheckConstraint(
            "education_requirement IS NULL OR education_requirement IN "
            "('high_school', 'diploma', 'associate', 'bachelor', 'master', "
            "'doctorate', 'unspecified_degree')",
            name="ck_job_parse_results_education_requirement",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    minimum_years_experience: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    education_requirement: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped[JobPosting] = relationship(back_populates="parse_result")
