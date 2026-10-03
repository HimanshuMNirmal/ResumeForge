"""Profile service: get-or-create and update helpers."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.models import User
from .models import Profile


async def get_or_create_profile(user_id: uuid.UUID, db: AsyncSession) -> Profile:
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        profile = Profile(
            user_id=user_id,
            full_name=user.name if user else None,
            email=user.email if user else None,
        )
        db.add(profile)
        await db.flush()
    return profile


async def apply_basics(profile: Profile, data: dict) -> Profile:
    for field, value in data.items():
        if value is not None:
            if field == "links":
                setattr(profile, field, [lnk.model_dump() if hasattr(lnk, "model_dump") else lnk for lnk in value])
            else:
                setattr(profile, field, value)
    return profile


async def apply_preferences(profile: Profile, data: dict) -> Profile:
    for field, value in data.items():
        if value is not None:
            setattr(profile, field, value)
    return profile


async def apply_experience(profile: Profile, experience: list) -> Profile:
    profile.experience = [e.model_dump() if hasattr(e, "model_dump") else e for e in experience]
    return profile


async def apply_skills(profile: Profile, skills: list, summary_facts: list | None, never_claim: list | None) -> Profile:
    profile.skills = [s.model_dump() if hasattr(s, "model_dump") else s for s in skills]
    if summary_facts is not None:
        profile.summary_facts = summary_facts
    if never_claim is not None:
        profile.never_claim = never_claim
    return profile


async def apply_education(profile: Profile, education: list, certifications: list | None) -> Profile:
    profile.education = [e.model_dump() if hasattr(e, "model_dump") else e for e in education]
    if certifications is not None:
        profile.certifications = [c.model_dump() if hasattr(c, "model_dump") else c for c in certifications]
    return profile


async def apply_projects(profile: Profile, projects: list) -> Profile:
    profile.projects = [p.model_dump() if hasattr(p, "model_dump") else p for p in projects]
    return profile
