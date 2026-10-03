"""ORM model for user API keys (encrypted at rest)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        # Only one active key per user enforced at DB level
        UniqueConstraint("user_id", name="uq_api_keys_one_active_per_user",
                         postgresql_where="is_active = true"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)   # anthropic | openai | gemini
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)    # AES-256-GCM ciphertext (base64)
    key_preview: Mapped[str] = mapped_column(String(8), nullable=False) # last 4 chars for display
    model_fast: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_strong: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship("User", back_populates="api_keys")  # noqa: F821
