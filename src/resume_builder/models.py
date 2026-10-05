"""Pydantic models: Profile (source of truth), JD (parsed posting), Resume (renderer input)."""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- profile
class Link(BaseModel):
    label: str
    url: str


class Basics(BaseModel):
    name: str
    email: str
    phone: str = ""
    location: str = ""
    links: list[Link] = Field(default_factory=list)


class Preferences(BaseModel):
    career_stage: Literal["experienced", "early_career"] = "experienced"
    max_pages: int = 1
    date_format: str = "MMM YYYY"
    paper_size: Literal["Letter", "A4"] = "Letter"


class Skill(BaseModel):
    name: str
    category: str = "Other"
    aliases: list[str] = Field(default_factory=list)
    years: Optional[float] = None
    level: str = "working"  # strong | working | familiar


class Bullet(BaseModel):
    id: str
    text: str
    skills: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)


class Experience(BaseModel):
    id: str
    company: str
    title: str
    title_aliases: list[str] = Field(default_factory=list)
    location: str = ""
    start: str
    end: Optional[str] = None
    bullets: list[Bullet] = Field(default_factory=list)


class Project(BaseModel):
    id: str
    name: str
    url: str = ""
    skills: list[str] = Field(default_factory=list)
    bullets: list[Bullet] = Field(default_factory=list)


class Education(BaseModel):
    id: str
    institution: str
    degree: str
    location: str = ""
    start: str = ""
    end: Optional[str] = None
    details: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    name: str
    issuer: str = ""
    date: str = ""


class Profile(BaseModel):
    basics: Basics
    preferences: Preferences = Field(default_factory=Preferences)
    summary_facts: list[str] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    never_claim: list[str] = Field(default_factory=list)

    def all_bullets(self) -> dict[str, Bullet]:
        out: dict[str, Bullet] = {}
        for e in self.experience:
            for b in e.bullets:
                out[b.id] = b
        for p in self.projects:
            for b in p.bullets:
                out[b.id] = b
        return out

    def full_text(self) -> str:
        """Every fact in the profile as one string (used to check summaries)."""
        parts = list(self.summary_facts)
        parts += [s.name for s in self.skills]
        for b in self.all_bullets().values():
            parts.append(b.text)
        for e in self.education:
            parts += [e.degree, e.institution, *e.details]
        return "\n".join(parts)

    def check_integrity(self, auto_heal: bool = True) -> list[str]:
        """Non-schema sanity checks (duplicate ids, bullet skills missing from skill list...)."""
        problems: list[str] = []
        seen: set[str] = set()
        for e in self.experience:
            for b in e.bullets:
                if b.id in seen:
                    problems.append(f"duplicate bullet id: {b.id}")
                seen.add(b.id)
        for p in self.projects:
            for b in p.bullets:
                if b.id in seen:
                    problems.append(f"duplicate bullet id: {b.id}")
                seen.add(b.id)

        def _norm(txt: str) -> str:
            return re.sub(r"[^a-z0-9]", "", str(txt).lower())

        names = {s.name.lower() for s in self.skills}
        norm_map = {_norm(s.name): s.name for s in self.skills}
        for s in self.skills:
            for a in s.aliases:
                names.add(a.lower())
                norm_map[_norm(a)] = s.name

        blocked = {n.lower() for n in self.never_claim}
        for bid, b in self.all_bullets().items():
            for idx, sk in enumerate(b.skills):
                sk_clean = str(sk).strip()
                if not sk_clean:
                    continue
                sk_lower = sk_clean.lower()
                sk_norm = _norm(sk_clean)
                if sk_lower in names:
                    continue
                if sk_norm and sk_norm in norm_map:
                    b.skills[idx] = norm_map[sk_norm]
                    continue
                if auto_heal:
                    from .taxonomy import classify_skill
                    new_skill = Skill(name=sk_clean, category=classify_skill(sk_clean))
                    self.skills.append(new_skill)
                    names.add(sk_lower)
                    if sk_norm:
                        norm_map[sk_norm] = sk_clean
                else:
                    problems.append(f"bullet {bid}: skill '{sk}' is not in profile.skills")

        for s in self.skills:
            if s.name.lower() in blocked:
                problems.append(f"skill '{s.name}' is also in never_claim")
        return problems


# ---------------------------------------------------------------- job description
class JD(BaseModel):
    company: str = ""
    title: str = ""
    seniority: str = ""
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    domain: str = ""
    notes: str = ""


# ---------------------------------------------------------------- resume (writer output)
class ResumeBullet(BaseModel):
    source_id: str  # provenance: id of the profile bullet this was derived from
    text: str


class ResumeExperience(BaseModel):
    id: str
    company: str
    title: str
    location: str = ""
    start: str
    end: Optional[str] = None
    bullets: list[ResumeBullet] = Field(default_factory=list)


class ResumeProject(BaseModel):
    id: str
    name: str
    url: str = ""
    bullets: list[ResumeBullet] = Field(default_factory=list)


class SkillGroup(BaseModel):
    category: str
    skills: list[str] = Field(default_factory=list)


class Resume(BaseModel):
    basics: Basics
    career_stage: Literal["experienced", "early_career"] = "experienced"
    date_format: str = "MMM YYYY"
    paper_size: Literal["Letter", "A4"] = "Letter"
    max_pages: int = 1
    target_role: str = ""
    summary: str = ""
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[ResumeExperience] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)

    @property
    def provenance(self) -> dict[str, str]:
        """Map 'entry_id#index' -> source bullet id (used by the validator)."""
        m: dict[str, str] = {}
        for e in self.experience:
            for i, b in enumerate(e.bullets):
                m[f"{e.id}#{i}"] = b.source_id
        for p in self.projects:
            for i, b in enumerate(p.bullets):
                m[f"{p.id}#{i}"] = b.source_id
        return m
