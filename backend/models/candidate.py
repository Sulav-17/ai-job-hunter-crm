from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.application import Application
    from backend.models.candidate_parse_result import (
        CandidateParseResult,
        CandidateSkill,
    )
    from backend.models.embedding import CandidateEmbedding, SemanticMatchResult
    from backend.models.match_result import MatchResult


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    __table_args__ = (
        CheckConstraint(
            "years_experience IS NULL OR "
            "(years_experience >= 0 AND years_experience <= 80)",
            name="ck_candidate_profiles_years_experience_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    professional_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    candidate_skills: Mapped[list[CandidateSkill]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    parse_result: Mapped[CandidateParseResult | None] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    match_results: Mapped[list[MatchResult]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    embedding: Mapped[CandidateEmbedding | None] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    semantic_match_results: Mapped[list[SemanticMatchResult]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
