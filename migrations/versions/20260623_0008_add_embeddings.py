"""add embeddings

Revision ID: 20260623_0008
Revises: 20260623_0007
Create Date: 2026-06-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision: str = "20260623_0008"
down_revision: str | Sequence[str] | None = "20260623_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "candidate_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
        sa.Column(
            "embedded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "dimensions > 0",
            name="ck_candidate_embeddings_dimensions_positive",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.id"],
            name="fk_candidate_embeddings_candidate_id_candidate_profiles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_embeddings"),
        sa.UniqueConstraint(
            "candidate_id",
            name="uq_candidate_embeddings_candidate_id",
        ),
    )
    op.create_index(
        "ix_candidate_embeddings_candidate_id",
        "candidate_embeddings",
        ["candidate_id"],
    )

    op.create_table(
        "job_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
        sa.Column(
            "embedded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "dimensions > 0",
            name="ck_job_embeddings_dimensions_positive",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["job_postings.id"],
            name="fk_job_embeddings_job_id_job_postings",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_embeddings"),
        sa.UniqueConstraint("job_id", name="uq_job_embeddings_job_id"),
    )
    op.create_index("ix_job_embeddings_job_id", "job_embeddings", ["job_id"])

    op.create_table(
        "semantic_match_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("cosine_similarity", sa.Numeric(), nullable=False),
        sa.Column("semantic_score", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("candidate_source_hash", sa.String(length=64), nullable=False),
        sa.Column("job_source_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "semantic_score >= 0 AND semantic_score <= 100",
            name="ck_semantic_match_results_semantic_score_range",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.id"],
            name="fk_semantic_match_results_candidate_id_candidate_profiles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["job_postings.id"],
            name="fk_semantic_match_results_job_id_job_postings",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_semantic_match_results"),
        sa.UniqueConstraint(
            "candidate_id",
            "job_id",
            name="uq_semantic_match_results_candidate_job",
        ),
    )
    op.create_index(
        "ix_semantic_match_results_candidate_id",
        "semantic_match_results",
        ["candidate_id"],
    )
    op.create_index(
        "ix_semantic_match_results_job_id",
        "semantic_match_results",
        ["job_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_semantic_match_results_job_id",
        table_name="semantic_match_results",
    )
    op.drop_index(
        "ix_semantic_match_results_candidate_id",
        table_name="semantic_match_results",
    )
    op.drop_table("semantic_match_results")
    op.drop_index("ix_job_embeddings_job_id", table_name="job_embeddings")
    op.drop_table("job_embeddings")
    op.drop_index(
        "ix_candidate_embeddings_candidate_id",
        table_name="candidate_embeddings",
    )
    op.drop_table("candidate_embeddings")
