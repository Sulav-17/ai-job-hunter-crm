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
    from backend.models.job import JobPosting


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job_skills: Mapped[list[JobSkill]] = relationship(
        back_populates="skill",
    )


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (
        CheckConstraint(
            "requirement_type IN ('required', 'preferred')",
            name="ck_job_skills_requirement_type",
        ),
        UniqueConstraint(
            "job_id",
            "skill_id",
            "requirement_type",
            name="uq_job_skills_job_skill_requirement",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id"),
        nullable=False,
    )
    requirement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped[JobPosting] = relationship(back_populates="job_skills")
    skill: Mapped[Skill] = relationship(back_populates="job_skills")
