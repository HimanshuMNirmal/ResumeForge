"""Add markdown column to resume_history

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resume_history",
        sa.Column("markdown", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resume_history", "markdown")
