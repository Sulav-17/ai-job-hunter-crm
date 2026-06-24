"""add tailoring results

Revision ID: 20260623_0009
Revises: 20260623_0008
Create Date: 2026-06-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260623_0009"
down_revision: str | Sequence[str] | None = "20260623_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tailoring_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("candidate_source_hash", sa.String(length=64), nullable=False),
        sa.Column("job_source_hash", sa.String(length=64), nullable=False),
        sa.Column("match_context_hash", sa.String(length=64), nullable=False),
        sa.Column("tailored_summary", sa.Text(), nullable=False),
        sa.Column("resume_bullets", postgresql.JSONB(), nullable=False),
        sa.Column("cover_letter", sa.Text(), nullable=False),
        sa.Column("keywords_used", postgresql.JSONB(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.id"],
            name="fk_tailoring_results_candidate_id_candidate_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["job_postings.id"],
            name="fk_tailoring_results_job_id_job_postings",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tailoring_results"),
        sa.UniqueConstraint(
            "candidate_id",
            "job_id",
            name="uq_tailoring_results_candidate_job",
        ),
    )
    op.create_index(
        "ix_tailoring_results_candidate_id",
        "tailoring_results",
        ["candidate_id"],
    )
    op.create_index(
        "ix_tailoring_results_job_id",
        "tailoring_results",
        ["job_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tailoring_results_job_id", table_name="tailoring_results")
    op.drop_index("ix_tailoring_results_candidate_id", table_name="tailoring_results")
    op.drop_table("tailoring_results")
