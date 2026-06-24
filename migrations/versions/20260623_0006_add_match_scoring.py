"""add match scoring

Revision ID: 20260623_0006
Revises: 20260623_0005
Create Date: 2026-06-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260623_0006"
down_revision: str | Sequence[str] | None = "20260623_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EDUCATION_VALUES = (
    "'high_school', 'diploma', 'associate', 'unspecified_degree', "
    "'bachelor', 'master', 'doctorate'"
)


def upgrade() -> None:
    op.create_table(
        "match_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("required_skill_score", sa.Integer(), nullable=True),
        sa.Column("preferred_skill_score", sa.Integer(), nullable=True),
        sa.Column("experience_score", sa.Integer(), nullable=True),
        sa.Column("education_score", sa.Integer(), nullable=True),
        sa.Column("matched_required_count", sa.Integer(), nullable=False),
        sa.Column("total_required_count", sa.Integer(), nullable=False),
        sa.Column("matched_preferred_count", sa.Integer(), nullable=False),
        sa.Column("total_preferred_count", sa.Integer(), nullable=False),
        sa.Column("candidate_years_used", sa.Integer(), nullable=True),
        sa.Column("required_years", sa.Integer(), nullable=True),
        sa.Column("candidate_education_level", sa.String(length=30), nullable=True),
        sa.Column("required_education_level", sa.String(length=30), nullable=True),
        sa.Column("scoring_version", sa.String(length=50), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100",
            name="ck_match_results_overall_score_range",
        ),
        sa.CheckConstraint(
            "required_skill_score IS NULL OR "
            "(required_skill_score >= 0 AND required_skill_score <= 100)",
            name="ck_match_results_required_skill_score_range",
        ),
        sa.CheckConstraint(
            "preferred_skill_score IS NULL OR "
            "(preferred_skill_score >= 0 AND preferred_skill_score <= 100)",
            name="ck_match_results_preferred_skill_score_range",
        ),
        sa.CheckConstraint(
            "experience_score IS NULL OR "
            "(experience_score >= 0 AND experience_score <= 100)",
            name="ck_match_results_experience_score_range",
        ),
        sa.CheckConstraint(
            "education_score IS NULL OR "
            "(education_score >= 0 AND education_score <= 100)",
            name="ck_match_results_education_score_range",
        ),
        sa.CheckConstraint(
            "matched_required_count >= 0 AND total_required_count >= 0 AND "
            "matched_preferred_count >= 0 AND total_preferred_count >= 0",
            name="ck_match_results_counts_non_negative",
        ),
        sa.CheckConstraint(
            "matched_required_count <= total_required_count",
            name="ck_match_results_required_count_bounds",
        ),
        sa.CheckConstraint(
            "matched_preferred_count <= total_preferred_count",
            name="ck_match_results_preferred_count_bounds",
        ),
        sa.CheckConstraint(
            "candidate_years_used IS NULL OR candidate_years_used >= 0",
            name="ck_match_results_candidate_years_non_negative",
        ),
        sa.CheckConstraint(
            "required_years IS NULL OR required_years >= 0",
            name="ck_match_results_required_years_non_negative",
        ),
        sa.CheckConstraint(
            "candidate_education_level IS NULL OR candidate_education_level IN "
            f"({EDUCATION_VALUES})",
            name="ck_match_results_candidate_education_level",
        ),
        sa.CheckConstraint(
            "required_education_level IS NULL OR required_education_level IN "
            f"({EDUCATION_VALUES})",
            name="ck_match_results_required_education_level",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.id"],
            name="fk_match_results_candidate_id_candidate_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["job_postings.id"],
            name="fk_match_results_job_id_job_postings",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_id",
            "job_id",
            name="uq_match_results_candidate_job",
        ),
    )
    op.create_index("ix_match_results_candidate_id", "match_results", ["candidate_id"])
    op.create_index("ix_match_results_job_id", "match_results", ["job_id"])

    op.create_table(
        "match_skill_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_result_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("requirement_type", sa.String(length=20), nullable=False),
        sa.Column("matched", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "requirement_type IN ('required', 'preferred')",
            name="ck_match_skill_details_requirement_type",
        ),
        sa.ForeignKeyConstraint(
            ["match_result_id"],
            ["match_results.id"],
            name="fk_match_skill_details_match_result_id_match_results",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            name="fk_match_skill_details_skill_id_skills",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_result_id",
            "skill_id",
            "requirement_type",
            name="uq_match_skill_details_result_skill_requirement",
        ),
    )
    op.create_index(
        "ix_match_skill_details_match_result_id",
        "match_skill_details",
        ["match_result_id"],
    )
    op.create_index(
        "ix_match_skill_details_skill_id",
        "match_skill_details",
        ["skill_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_match_skill_details_skill_id", table_name="match_skill_details")
    op.drop_index(
        "ix_match_skill_details_match_result_id",
        table_name="match_skill_details",
    )
    op.drop_table("match_skill_details")
    op.drop_index("ix_match_results_job_id", table_name="match_results")
    op.drop_index("ix_match_results_candidate_id", table_name="match_results")
    op.drop_table("match_results")
