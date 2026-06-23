"""create job postings

Revision ID: 20260623_0003
Revises: 20260623_0002
Create Date: 2026-06-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260623_0003"
down_revision: str | Sequence[str] | None = "20260623_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_postings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("company", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=True),
        sa.Column("employment_type", sa.String(length=30), nullable=True),
        sa.Column("work_mode", sa.String(length=20), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(title)) > 0",
            name="ck_job_postings_title_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(company)) > 0",
            name="ck_job_postings_company_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(btrim(description)) >= 50",
            name="ck_job_postings_description_min_length",
        ),
        sa.CheckConstraint(
            "employment_type IS NULL OR employment_type IN "
            "('full_time', 'part_time', 'contract', 'internship', "
            "'temporary', 'other')",
            name="ck_job_postings_employment_type",
        ),
        sa.CheckConstraint(
            "work_mode IS NULL OR work_mode IN ('remote', 'hybrid', 'on_site')",
            name="ck_job_postings_work_mode",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("job_postings")
