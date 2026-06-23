from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
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
    from backend.models.skill import Skill


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "skill_id",
            name="uq_candidate_skills_candidate_skill",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id"),
        nullable=False,
    )
    evidence_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    candidate: Mapped[CandidateProfile] = relationship(
        back_populates="candidate_skills",
    )
    skill: Mapped[Skill] = relationship(back_populates="candidate_skills")


class CandidateParseResult(Base):
    __tablename__ = "candidate_parse_results"
    __table_args__ = (
        CheckConstraint(
            "parsed_years_experience IS NULL OR parsed_years_experience >= 0",
            name="ck_candidate_parse_results_years_non_negative",
        ),
        CheckConstraint(
            "education_level IS NULL OR education_level IN "
            "('high_school', 'diploma', 'associate', 'bachelor', 'master', "
            "'doctorate', 'unspecified_degree')",
            name="ck_candidate_parse_results_education_level",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    parsed_years_experience: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    education_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    candidate: Mapped[CandidateProfile] = relationship(
        back_populates="parse_result",
    )
