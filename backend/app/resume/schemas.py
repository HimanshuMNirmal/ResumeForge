"""Pydantic schemas for the resume build endpoint."""
from __future__ import annotations

from pydantic import BaseModel, Field


class BuildRequest(BaseModel):
    jd_text: str = Field(min_length=50, description="The full job description text")
    company: str | None = None
    title: str | None = None
    use_pdf: bool = True
