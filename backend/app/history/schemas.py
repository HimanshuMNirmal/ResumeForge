"""Pydantic schemas for history responses."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator


class HistoryItemOut(BaseModel):
    id: uuid.UUID
    jd_title: Optional[str]
    jd_company: Optional[str]
    ats_score: Optional[int]
    model_used: Optional[str]
    provider_used: Optional[str]
    has_docx: bool
    has_pdf: bool
    download_docx_url: Optional[str]  # presigned — populated in router
    download_pdf_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryListOut(BaseModel):
    items: list[HistoryItemOut]
    total: int
    limit: int
    offset: int


class HistoryDetailOut(HistoryItemOut):
    jd_text: str
    notes: Optional[str]
