"""add demo markers

Revision ID: 20260625_0010
Revises: 20260623_0009
Create Date: 2026-06-25

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260625_0010"
down_revision: str | Sequence[str] | None = "20260623_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ROOT_TABLES = ("candidate_profiles", "job_postings", "applications")


def upgrade() -> None:
    for table_name in ROOT_TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "is_demo",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
        )
        op.add_column(
            table_name,
            sa.Column("demo_seed_key", sa.String(length=160), nullable=True),
        )
        op.create_index(
            f"ix_{table_name}_is_demo",
            table_name,
            ["is_demo"],
        )
        op.create_index(
            f"uq_{table_name}_demo_seed_key",
            table_name,
            ["demo_seed_key"],
            unique=True,
            postgresql_where=sa.text("demo_seed_key IS NOT NULL"),
        )


def downgrade() -> None:
    for table_name in reversed(ROOT_TABLES):
        op.drop_index(f"uq_{table_name}_demo_seed_key", table_name=table_name)
        op.drop_index(f"ix_{table_name}_is_demo", table_name=table_name)
        op.drop_column(table_name, "demo_seed_key")
        op.drop_column(table_name, "is_demo")
