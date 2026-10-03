"""Pydantic schemas for API key management."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Provider = Literal["anthropic", "openai", "gemini"]


class AddKeyRequest(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    provider: Provider
    raw_key: str = Field(min_length=10, description="The raw API key (will be encrypted)")
    model_fast: Optional[str] = None
    model_strong: Optional[str] = None


class KeyOut(BaseModel):
    id: uuid.UUID
    label: str
    provider: str
    key_preview: str         # last 4 chars, e.g. "xK9z"
    model_fast: Optional[str]
    model_strong: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AvailableModelsOut(BaseModel):
    provider: str
    fast_models: list[str]
    strong_models: list[str]
