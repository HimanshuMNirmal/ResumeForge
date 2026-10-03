"""ORM model for resume generation history."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ResumeHistory(Base):
    __tablename__ = "resume_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jd_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jd_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)

    # S3 object keys ONLY — no base URL (injected at runtime from env)
    s3_key_docx: Mapped[str | None] = mapped_column(Text, nullable=True)
    s3_key_pdf: Mapped[str | None] = mapped_column(Text, nullable=True)

    ats_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of notes
    markdown: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="resume_history")  # noqa: F821
