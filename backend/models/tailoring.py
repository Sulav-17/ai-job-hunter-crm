from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.candidate import CandidateProfile
    from backend.models.job import JobPosting


class TailoringResult(Base):
    __tablename__ = "tailoring_results"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "job_id",
            name="uq_tailoring_results_candidate_job",
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
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    candidate_source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    job_source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    match_context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    tailored_summary: Mapped[str] = mapped_column(Text, nullable=False)
    resume_bullets: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    cover_letter: Mapped[str] = mapped_column(Text, nullable=False)
    keywords_used: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    candidate: Mapped[CandidateProfile] = relationship(
        back_populates="tailoring_results",
    )
    job: Mapped[JobPosting] = relationship(back_populates="tailoring_results")
