"""Step 4: tailoring writer. The LLM only rewords selected facts; code owns every locked field."""
from __future__ import annotations

import json

from .llm import LLMClient, load_prompt, strong_model
from .matcher import Selection
from .models import (
    JD, Profile, Resume, ResumeBullet, ResumeExperience, ResumeProject,
)
from .textutil import SkillIndex

MAX_RETRIES = 2

_BULLETS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"source_id": {"type": "string"}, "text": {"type": "string"}},
        "required": ["source_id", "text"],
    },
}
WRITER_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "title": {"type": "string"}, "bullets": _BULLETS},
                "required": ["id", "bullets"],
            },
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "bullets": _BULLETS},
                "required": ["id", "bullets"],
            },
        },
    },
    "required": ["summary", "experience"],
}


# ------------------------------------------------------------------ deterministic baseline
def fallback_summary(profile: Profile, jd: JD, sel: Selection) -> str:
    parts: list[str] = []
    for fact in profile.summary_facts[:3]:
        fact = fact.strip().rstrip(".")
        if fact:
            parts.append(fact[0].upper() + fact[1:] + ".")
    top = [t for t in sel.matched_must if SkillIndex(profile).is_supported(t)][:4]
    if top:
        # Use a natural sentence instead of a colon-separated list to avoid grammar-checker flags
        skills_str = ", ".join(top[:-1]) + " and " + top[-1] if len(top) > 1 else top[0]
        parts.append(f"Key strengths include {skills_str}.")
    return " ".join(parts)


def base_resume(profile: Profile, jd: JD, sel: Selection) -> Resume:
    """Selected facts, un-reworded. Always valid; used with --no-llm and as the retry fallback."""
    pr = profile.preferences
    return Resume(
        basics=profile.basics,
        career_stage=pr.career_stage,
        date_format=pr.date_format,
        paper_size=pr.paper_size,
        max_pages=pr.max_pages,
        target_role=jd.title,
        summary=fallback_summary(profile, jd, sel),
        skills=sel.skill_groups,
        experience=[
            ResumeExperience(
                id=e.id, company=e.company, title=e.title, location=e.location, start=e.start, end=e.end,
                bullets=[ResumeBullet(source_id=b.id, text=b.text) for b in bullets],
            )
            for e, bullets in sel.experience
        ],
        projects=[
            ResumeProject(
                id=p.id, name=p.name, url=p.url,
                bullets=[ResumeBullet(source_id=b.id, text=b.text) for b in bullets],
            )
            for p, bullets in sel.projects
        ],
        education=profile.education,
        certifications=profile.certifications,
    )


# ------------------------------------------------------------------ LLM path
def _user_prompt(profile: Profile, jd: JD, sel: Selection, errors: list[str] | None) -> str:
    lines = ["TARGET JOB", json.dumps(jd.model_dump(), indent=2), ""]
    lines += ["NEVER CLAIM", ", ".join(profile.never_claim) or "(none)", ""]
    lines += ["SUMMARY FACTS"] + [f"- {f}" for f in profile.summary_facts] + [""]
    lines += ["SELECTED SKILLS"]
    lines += [f"- {g.category}: {', '.join(g.skills)}" for g in sel.skill_groups] + [""]
    lines += ["EXPERIENCE"]
    for e, bullets in sel.experience:
        allowed = [e.title, *e.title_aliases]
        lines.append(f"* id={e.id} | {e.company} | allowed titles: {allowed}")
        lines += [f"    - source_id={b.id}: {b.text}" for b in bullets]
    if sel.projects:
        lines += ["", "PROJECTS"]
        for p, bullets in sel.projects:
            lines.append(f"* id={p.id} | {p.name}")
            lines += [f"    - source_id={b.id}: {b.text}" for b in bullets]
    if errors:
        lines += ["", "YOUR PREVIOUS ATTEMPT WAS REJECTED. FIX THESE ERRORS:"] + [f"- {e}" for e in errors]
    return "\n".join(lines)


def _assemble(base: Resume, data: dict) -> Resume:
    """Merge model output into the baseline. Locked fields (company, dates...) always come from the baseline."""
    exp_by_id = {e["id"]: e for e in data.get("experience", []) if isinstance(e, dict) and "id" in e}
    proj_by_id = {p["id"]: p for p in data.get("projects", []) if isinstance(p, dict) and "id" in p}

    def bullets(raw) -> list[ResumeBullet]:
        return [ResumeBullet(source_id=str(b["source_id"]), text=str(b["text"]).strip()) for b in raw]

    experience = []
    for e in base.experience:
        d = exp_by_id.get(e.id)
        experience.append(
            ResumeExperience(
                id=e.id, company=e.company, location=e.location, start=e.start, end=e.end,
                title=(d.get("title") or e.title) if d else e.title,
                bullets=bullets(d["bullets"]) if d else e.bullets,
            )
        )
    projects = []
    for p in base.projects:
        d = proj_by_id.get(p.id)
        projects.append(
            ResumeProject(id=p.id, name=p.name, url=p.url, bullets=bullets(d["bullets"]) if d else p.bullets)
        )
    return Resume(
        basics=base.basics, career_stage=base.career_stage, date_format=base.date_format,
        paper_size=base.paper_size, max_pages=base.max_pages, target_role=base.target_role,
        summary=str(data.get("summary") or base.summary).strip(), skills=base.skills,
        experience=experience, projects=projects, education=base.education,
        certifications=base.certifications,
    )


def tailor(
    profile: Profile, jd: JD, sel: Selection, client: LLMClient | None
) -> tuple[Resume, list[str]]:
    """Returns (resume, notes). Retries with validator feedback, then falls back to the baseline."""
    from .validator import validate  # local import: validator imports jd_parser constants

    base = base_resume(profile, jd, sel)
    if client is None:
        return base, ["LLM disabled: used selected bullets and a fact-only summary, no rewording."]

    errors: list[str] | None = None
    notes: list[str] = []
    for attempt in range(MAX_RETRIES + 1):
        try:
            data = client.structured(
                model=strong_model(),
                system=load_prompt("writer.md"),
                user=_user_prompt(profile, jd, sel, errors),
                tool_name="write_resume",
                schema=WRITER_SCHEMA,
            )
            candidate = _assemble(base, data)
        except Exception as e:
            notes.append(f"Writer attempt {attempt + 1} failed to produce usable output: {e}")
            errors = [f"output could not be parsed: {e}"]
            continue
        errors = validate(candidate, profile, jd, sel)
        if not errors:
            if attempt:
                notes.append(f"Writer passed validation on retry {attempt}.")
            return candidate, notes
        notes.append(f"Writer attempt {attempt + 1} rejected: {len(errors)} validation error(s).")
    notes.append("Writer never passed validation: fell back to un-reworded selected bullets.")
    notes += [f"  last error: {e}" for e in (errors or [])[:5]]
    return base, notes
