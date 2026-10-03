"""Initial schema: users, refresh_tokens, profiles, api_keys, resume_history

Revision ID: 0001
Revises:
Create Date: 2026-10-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── refresh_tokens ─────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    # ── profiles ───────────────────────────────────────────────────────────
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("full_name", sa.Text, nullable=True),
        sa.Column("email", sa.Text, nullable=True),
        sa.Column("phone", sa.Text, nullable=True),
        sa.Column("location", sa.Text, nullable=True),
        sa.Column("links", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("career_stage", sa.Text, nullable=False, server_default="experienced"),
        sa.Column("max_pages", sa.Integer, nullable=False, server_default="1"),
        sa.Column("date_format", sa.Text, nullable=False, server_default="MMM YYYY"),
        sa.Column("paper_size", sa.Text, nullable=False, server_default="Letter"),
        sa.Column("summary_facts", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("skills", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("experience", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("projects", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("education", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("certifications", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("never_claim", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── api_keys ───────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("encrypted_key", sa.Text, nullable=False),
        sa.Column("key_preview", sa.String(8), nullable=False),
        sa.Column("model_fast", sa.String(100), nullable=True),
        sa.Column("model_strong", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # Only one active key per user — partial unique index
    op.execute(
        "CREATE UNIQUE INDEX uq_api_keys_one_active ON api_keys(user_id) WHERE is_active = true"
    )

    # ── resume_history ─────────────────────────────────────────────────────
    op.create_table(
        "resume_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("jd_title", sa.String(255), nullable=True),
        sa.Column("jd_company", sa.String(255), nullable=True),
        sa.Column("jd_text", sa.Text, nullable=False),
        sa.Column("s3_key_docx", sa.Text, nullable=True),
        sa.Column("s3_key_pdf", sa.Text, nullable=True),
        sa.Column("ats_score", sa.Integer, nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("provider_used", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_resume_history_user_id", "resume_history", ["user_id"])
    op.create_index("ix_resume_history_created_at", "resume_history", ["created_at"])


def downgrade() -> None:
    op.drop_table("resume_history")
    op.execute("DROP INDEX IF EXISTS uq_api_keys_one_active")
    op.drop_table("api_keys")
    op.drop_table("profiles")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
