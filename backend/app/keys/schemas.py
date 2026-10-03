"""Pydantic schemas for API key management."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, computed_field, model_validator

Provider = Literal["anthropic", "openai", "gemini"]


class AddKeyRequest(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    provider: Provider
    raw_key: Optional[str] = Field(default=None, min_length=10, description="The raw API key (will be encrypted)")
    api_key: Optional[str] = Field(default=None, min_length=10, description="Alias for raw_key")
    model_fast: Optional[str] = None
    model_strong: Optional[str] = None

    @model_validator(mode="after")
    def resolve_key(self) -> AddKeyRequest:
        key = self.raw_key or self.api_key
        if not key:
            raise ValueError("api_key or raw_key is required")
        self.raw_key = key
        return self


class KeyOut(BaseModel):
    id: uuid.UUID
    label: str
    provider: str
    key_preview: str         # last 4 chars, e.g. "xK9z"
    model_fast: Optional[str]
    model_strong: Optional[str]
    is_active: bool
    created_at: datetime

    @computed_field
    @property
    def key_hint(self) -> str:
        return f"...{self.key_preview}" if self.key_preview else ""

    model_config = {"from_attributes": True}


class AvailableModelsOut(BaseModel):
    provider: str
    fast_models: list[str] = []
    strong_models: list[str] = []
    providers: dict[str, list[str]] = {}
    platform_defaults: list[str] = []
