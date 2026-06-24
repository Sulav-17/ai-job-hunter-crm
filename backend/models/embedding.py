from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.candidate import CandidateProfile
    from backend.models.job import JobPosting


class CandidateEmbedding(Base):
    __tablename__ = "candidate_embeddings"
    __table_args__ = (
        CheckConstraint(
            "dimensions > 0",
            name="ck_candidate_embeddings_dimensions_positive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(), nullable=False)
    embedded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    candidate: Mapped[CandidateProfile] = relationship(
        back_populates="embedding",
    )


class JobEmbedding(Base):
    __tablename__ = "job_embeddings"
    __table_args__ = (
        CheckConstraint(
            "dimensions > 0",
            name="ck_job_embeddings_dimensions_positive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(), nullable=False)
    embedded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped[JobPosting] = relationship(back_populates="embedding")


class SemanticMatchResult(Base):
    __tablename__ = "semantic_match_results"
    __table_args__ = (
        CheckConstraint(
            "semantic_score >= 0 AND semantic_score <= 100",
            name="ck_semantic_match_results_semantic_score_range",
        ),
        UniqueConstraint(
            "candidate_id",
            "job_id",
            name="uq_semantic_match_results_candidate_job",
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
    cosine_similarity: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    semantic_score: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    candidate_source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    job_source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    candidate: Mapped[CandidateProfile] = relationship(
        back_populates="semantic_match_results",
    )
    job: Mapped[JobPosting] = relationship(back_populates="semantic_match_results")
