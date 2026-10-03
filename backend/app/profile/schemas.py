"""Pydantic schemas for profile API — mirrors the core engine models.py structure."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Shared sub-models ─────────────────────────────────────────────────────────

class LinkSchema(BaseModel):
    label: str
    url: str


class SkillSchema(BaseModel):
    name: str
    category: str = "Other"
    aliases: list[str] = Field(default_factory=list)
    years: Optional[float] = None
    level: str = "working"


class BulletSchema(BaseModel):
    id: str
    text: str
    skills: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)


class ExperienceSchema(BaseModel):
    id: str
    company: str
    title: str
    title_aliases: list[str] = Field(default_factory=list)
    location: str = ""
    start: str
    end: Optional[str] = None
    bullets: list[BulletSchema] = Field(default_factory=list)


class ProjectSchema(BaseModel):
    id: str
    name: str
    url: str = ""
    skills: list[str] = Field(default_factory=list)
    bullets: list[BulletSchema] = Field(default_factory=list)


class EducationSchema(BaseModel):
    id: str
    institution: str
    degree: str
    location: str = ""
    start: str = ""
    end: Optional[str] = None
    details: list[str] = Field(default_factory=list)


class CertificationSchema(BaseModel):
    name: str
    issuer: str = ""
    date: str = ""


# ── Section-level PATCH schemas ───────────────────────────────────────────────

class BasicsUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    links: Optional[list[LinkSchema]] = None


class PreferencesUpdate(BaseModel):
    career_stage: Optional[Literal["experienced", "early_career"]] = None
    max_pages: Optional[int] = Field(default=None, ge=1, le=10)
    date_format: Optional[str] = None
    paper_size: Optional[Literal["Letter", "A4"]] = None


class ExperienceUpdate(BaseModel):
    experience: list[ExperienceSchema]


class SkillsUpdate(BaseModel):
    skills: list[SkillSchema]
    summary_facts: Optional[list[str]] = None
    never_claim: Optional[list[str]] = None


class EducationUpdate(BaseModel):
    education: list[EducationSchema]
    certifications: Optional[list[CertificationSchema]] = None


class ProjectsUpdate(BaseModel):
    projects: list[ProjectSchema]


# ── Full profile response ─────────────────────────────────────────────────────

class ProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    links: list[LinkSchema]
    career_stage: str
    max_pages: int
    date_format: str
    paper_size: str
    summary_facts: list[str]
    skills: list[SkillSchema]
    experience: list[ExperienceSchema]
    projects: list[ProjectSchema]
    education: list[EducationSchema]
    certifications: list[CertificationSchema]
    never_claim: list[str]
    updated_at: datetime

    model_config = {"from_attributes": True}
