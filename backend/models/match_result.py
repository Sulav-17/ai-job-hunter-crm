from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.candidate import CandidateProfile
    from backend.models.job import JobPosting
    from backend.models.skill import Skill

EDUCATION_VALUES = (
    "'high_school', 'diploma', 'associate', 'unspecified_degree', "
    "'bachelor', 'master', 'doctorate'"
)


class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (
        CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100",
            name="ck_match_results_overall_score_range",
        ),
        CheckConstraint(
            "required_skill_score IS NULL OR "
            "(required_skill_score >= 0 AND required_skill_score <= 100)",
            name="ck_match_results_required_skill_score_range",
        ),
        CheckConstraint(
            "preferred_skill_score IS NULL OR "
            "(preferred_skill_score >= 0 AND preferred_skill_score <= 100)",
            name="ck_match_results_preferred_skill_score_range",
        ),
        CheckConstraint(
            "experience_score IS NULL OR "
            "(experience_score >= 0 AND experience_score <= 100)",
            name="ck_match_results_experience_score_range",
        ),
        CheckConstraint(
            "education_score IS NULL OR "
            "(education_score >= 0 AND education_score <= 100)",
            name="ck_match_results_education_score_range",
        ),
        CheckConstraint(
            "matched_required_count >= 0 AND total_required_count >= 0 AND "
            "matched_preferred_count >= 0 AND total_preferred_count >= 0",
            name="ck_match_results_counts_non_negative",
        ),
        CheckConstraint(
            "matched_required_count <= total_required_count",
            name="ck_match_results_required_count_bounds",
        ),
        CheckConstraint(
            "matched_preferred_count <= total_preferred_count",
            name="ck_match_results_preferred_count_bounds",
        ),
        CheckConstraint(
            "candidate_years_used IS NULL OR candidate_years_used >= 0",
            name="ck_match_results_candidate_years_non_negative",
        ),
        CheckConstraint(
            "required_years IS NULL OR required_years >= 0",
            name="ck_match_results_required_years_non_negative",
        ),
        CheckConstraint(
            "candidate_education_level IS NULL OR candidate_education_level IN "
            f"({EDUCATION_VALUES})",
            name="ck_match_results_candidate_education_level",
        ),
        CheckConstraint(
            "required_education_level IS NULL OR required_education_level IN "
            f"({EDUCATION_VALUES})",
            name="ck_match_results_required_education_level",
        ),
        UniqueConstraint(
            "candidate_id",
            "job_id",
            name="uq_match_results_candidate_job",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    required_skill_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_skill_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    education_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matched_required_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_required_count: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_preferred_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_preferred_count: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_years_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_education_level: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    required_education_level: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    scoring_version: Mapped[str] = mapped_column(String(50), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    candidate: Mapped[CandidateProfile] = relationship(back_populates="match_results")
    job: Mapped[JobPosting] = relationship(back_populates="match_results")
    skill_details: Mapped[list[MatchSkillDetail]] = relationship(
        back_populates="match_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class MatchSkillDetail(Base):
    __tablename__ = "match_skill_details"
    __table_args__ = (
        CheckConstraint(
            "requirement_type IN ('required', 'preferred')",
            name="ck_match_skill_details_requirement_type",
        ),
        UniqueConstraint(
            "match_result_id",
            "skill_id",
            "requirement_type",
            name="uq_match_skill_details_result_skill_requirement",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_result_id: Mapped[int] = mapped_column(
        ForeignKey("match_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id"),
        nullable=False,
        index=True,
    )
    requirement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    match_result: Mapped[MatchResult] = relationship(back_populates="skill_details")
    skill: Mapped[Skill] = relationship(back_populates="match_skill_details")
