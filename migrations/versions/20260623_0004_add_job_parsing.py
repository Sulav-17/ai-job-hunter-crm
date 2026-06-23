"""add job parsing

Revision ID: 20260623_0004
Revises: 20260623_0003
Create Date: 2026-06-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260623_0004"
down_revision: str | Sequence[str] | None = "20260623_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name", name="uq_skills_normalized_name"),
    )

    op.create_table(
        "job_skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("requirement_type", sa.String(length=20), nullable=False),
        sa.Column("evidence_text", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "requirement_type IN ('required', 'preferred')",
            name="ck_job_skills_requirement_type",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["job_postings.id"],
            name="fk_job_skills_job_id_job_postings",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            name="fk_job_skills_skill_id_skills",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "skill_id",
            "requirement_type",
            name="uq_job_skills_job_skill_requirement",
        ),
    )
    op.create_index("ix_job_skills_job_id", "job_skills", ["job_id"])
    op.create_index("ix_job_skills_skill_id", "job_skills", ["skill_id"])

    op.create_table(
        "job_parse_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("minimum_years_experience", sa.Integer(), nullable=True),
        sa.Column("education_requirement", sa.String(length=30), nullable=True),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column(
            "parsed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "minimum_years_experience IS NULL OR minimum_years_experience >= 0",
            name="ck_job_parse_results_minimum_years_non_negative",
        ),
        sa.CheckConstraint(
            "education_requirement IS NULL OR education_requirement IN "
            "('high_school', 'diploma', 'associate', 'bachelor', 'master', "
            "'doctorate', 'unspecified_degree')",
            name="ck_job_parse_results_education_requirement",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["job_postings.id"],
            name="fk_job_parse_results_job_id_job_postings",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_job_parse_results_job_id"),
    )
    op.create_index("ix_job_parse_results_job_id", "job_parse_results", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_parse_results_job_id", table_name="job_parse_results")
    op.drop_table("job_parse_results")
    op.drop_index("ix_job_skills_skill_id", table_name="job_skills")
    op.drop_index("ix_job_skills_job_id", table_name="job_skills")
    op.drop_table("job_skills")
    op.drop_table("skills")
