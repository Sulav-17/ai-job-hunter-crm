"""add candidate parsing

Revision ID: 20260623_0005
Revises: 20260623_0004
Create Date: 2026-06-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260623_0005"
down_revision: str | Sequence[str] | None = "20260623_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("evidence_text", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.id"],
            name="fk_candidate_skills_candidate_id_candidate_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            name="fk_candidate_skills_skill_id_skills",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_id",
            "skill_id",
            name="uq_candidate_skills_candidate_skill",
        ),
    )
    op.create_index(
        "ix_candidate_skills_candidate_id",
        "candidate_skills",
        ["candidate_id"],
    )
    op.create_index("ix_candidate_skills_skill_id", "candidate_skills", ["skill_id"])

    op.create_table(
        "candidate_parse_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("parsed_years_experience", sa.Integer(), nullable=True),
        sa.Column("education_level", sa.String(length=30), nullable=True),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column(
            "parsed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "parsed_years_experience IS NULL OR parsed_years_experience >= 0",
            name="ck_candidate_parse_results_years_non_negative",
        ),
        sa.CheckConstraint(
            "education_level IS NULL OR education_level IN "
            "('high_school', 'diploma', 'associate', 'bachelor', 'master', "
            "'doctorate', 'unspecified_degree')",
            name="ck_candidate_parse_results_education_level",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.id"],
            name="fk_candidate_parse_results_candidate_id_candidate_profiles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", name="uq_candidate_parse_results_candidate_id"),
    )
    op.create_index(
        "ix_candidate_parse_results_candidate_id",
        "candidate_parse_results",
        ["candidate_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_parse_results_candidate_id",
        table_name="candidate_parse_results",
    )
    op.drop_table("candidate_parse_results")
    op.drop_index("ix_candidate_skills_skill_id", table_name="candidate_skills")
    op.drop_index("ix_candidate_skills_candidate_id", table_name="candidate_skills")
    op.drop_table("candidate_skills")
