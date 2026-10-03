"""Step 5: truthfulness + schema + length checks. Returns a list of human-readable errors (empty = pass)."""
from __future__ import annotations

import math
import re

from .jd_parser import COMMON_TECH
from .matcher import Selection
from .models import JD, Profile, Resume
from .textutil import (
    STRONG_VERBS, WEAK_VERBS, SkillIndex, numbers_in, term_in_text, words,
)

LINE_CHARS = 105  # characters per rendered line, roughly (Calibri 10.5pt, ~0.8in margins)
LINES_PER_PAGE = 54


def validate(resume: Resume, profile: Profile, jd: JD, selection: Selection | None = None) -> list[str]:
    errs: list[str] = []
    idx = SkillIndex(profile)
    p_bullets = profile.all_bullets()
    p_text = profile.full_text()
    jd_skills = [*jd.must_have, *jd.nice_to_have]
    selected = selection.selected_ids() if selection else None

    # ---- basics unchanged
    if resume.basics != profile.basics:
        errs.append("basics (name/contact) differ from the profile")

    # ---- experience: locked fields
    p_exp = {e.id: e for e in profile.experience}
    owned: dict[str, set[str]] = {e.id: {b.id for b in e.bullets} for e in profile.experience}
    owned.update({p.id: {b.id for b in p.bullets} for p in profile.projects})
    for e in resume.experience:
        src = p_exp.get(e.id)
        if src is None:
            errs.append(f"experience '{e.id}' does not exist in the profile")
            continue
        for fld in ("company", "start", "end", "location"):
            if getattr(e, fld) != getattr(src, fld):
                errs.append(f"{e.id}: {fld} changed ('{getattr(src, fld)}' -> '{getattr(e, fld)}')")
        if not _title_ok(e.title, src.title, src.title_aliases):
            errs.append(f"{e.id}: title '{e.title}' is not the real title or an allowed alias of '{src.title}'")

    # ---- projects / education / certifications
    p_proj = {p.id: p for p in profile.projects}
    for pr in resume.projects:
        src = p_proj.get(pr.id)
        if src is None or src.name != pr.name:
            errs.append(f"project '{pr.id}' does not match the profile")
    p_edu = {e.id: e for e in profile.education}
    for ed in resume.education:
        src = p_edu.get(ed.id)
        if src is None or (ed.degree, ed.institution, ed.start, ed.end) != (src.degree, src.institution, src.start, src.end):
            errs.append(f"education '{ed.id}' does not match the profile")
    cert_names = {c.name for c in profile.certifications}
    for c in resume.certifications:
        if c.name not in cert_names:
            errs.append(f"certification '{c.name}' is not in the profile")

    # ---- bullets: provenance + content
    for entry in [*resume.experience, *resume.projects]:
        seen_src: set[str] = set()
        for i, b in enumerate(entry.bullets):
            where = f"{entry.id} bullet {i + 1}"
            if b.source_id not in p_bullets:
                errs.append(f"{where}: source_id '{b.source_id}' not in profile")
                continue
            if b.source_id not in owned.get(entry.id, set()):
                errs.append(f"{where}: source '{b.source_id}' belongs to a different entry")
            if selected is not None and b.source_id not in selected:
                errs.append(f"{where}: source '{b.source_id}' was not one of the selected bullets")
            if b.source_id in seen_src:
                errs.append(f"{where}: source '{b.source_id}' used twice")
            seen_src.add(b.source_id)
            errs += _check_bullet(where, b.text, p_bullets[b.source_id], idx, profile, jd_skills)

    # ---- skills
    for g in resume.skills:
        for s in g.skills:
            base = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
            if idx.canon(base) is None and idx.canon(s) is None:
                errs.append(f"skill '{s}' is not in the profile")
            elif idx.is_blocked(base):
                errs.append(f"skill '{s}' is in never_claim")

    # ---- summary
    errs += _check_summary(resume.summary, profile, idx, jd_skills, p_text)

    # ---- length (estimate; the renderer measures the real page count)
    est = estimate_lines(resume)
    budget = LINES_PER_PAGE * max(1, resume.max_pages)
    if est > budget:
        errs.append(f"estimated length {est:.0f} lines exceeds budget of {budget} lines")
    return errs


def _title_ok(title: str, real: str, aliases: list[str]) -> bool:
    if title == real or title in aliases:
        return True
    m = re.fullmatch(re.escape(real) + r" \((.+)\)", title)
    return bool(m and any(m.group(1).lower() in a.lower() for a in aliases))


def _check_bullet(where, out, src, idx: SkillIndex, profile: Profile, jd_skills: list[str]) -> list[str]:
    errs: list[str] = []
    src_blob = " ".join([src.text, *src.skills])

    extra_nums = numbers_in(out) - numbers_in(src.text)
    if extra_nums:
        errs.append(f"{where}: numbers not in source bullet: {sorted(extra_nums)}")
    missing = [m for m in numbers_in(" ".join(src.metrics)) if m not in numbers_in(out)]
    if missing:
        errs.append(f"{where}: dropped metric value(s) {sorted(missing)} from the source bullet")

    for t in profile.never_claim:
        if term_in_text(t, out) and not term_in_text(t, src.text):
            errs.append(f"{where}: mentions never_claim item '{t}'")

    for t in jd_skills:
        if idx.text_has(t, out) and not idx.text_has(t, src_blob):
            errs.append(f"{where}: introduces '{t}', which is not in the source bullet")
    for t in COMMON_TECH:
        if term_in_text(t, out) and not idx.text_has(t, src_blob) and not term_in_text(t, src_blob):
            errs.append(f"{where}: introduces technology '{t}', which is not in the source bullet")

    out_w, src_w = words(out), words(src.text)
    if (src_w & WEAK_VERBS) and (out_w & STRONG_VERBS) - src_w:
        errs.append(f"{where}: upgrades seniority ({sorted((out_w & STRONG_VERBS) - src_w)})")
    return errs


def _check_summary(summary: str, profile: Profile, idx: SkillIndex, jd_skills, p_text: str) -> list[str]:
    errs: list[str] = []
    if len(summary) > 500:
        errs.append("summary is longer than 500 characters")
    for t in profile.never_claim:
        if term_in_text(t, summary):
            errs.append(f"summary mentions never_claim item '{t}'")
    extra = numbers_in(summary) - numbers_in(p_text)
    if extra:
        errs.append(f"summary contains numbers not found in the profile: {sorted(extra)}")
    for t in [*jd_skills, *COMMON_TECH]:
        if idx.text_has(t, summary) and not idx.text_has(t, p_text) and not term_in_text(t, p_text):
            errs.append(f"summary claims '{t}', which is not supported by the profile")
    return errs


def estimate_lines(resume: Resume) -> float:
    """Rough line count so obviously-too-long resumes are caught before rendering."""
    def n(text: str, width: int = LINE_CHARS) -> int:
        return max(1, math.ceil(len(text) / width))

    lines = 3.0  # name + contact
    if resume.summary:
        lines += 2 + n(resume.summary)
    if resume.skills:
        lines += 2 + sum(n(f"{g.category}: {', '.join(g.skills)}") for g in resume.skills)
    if resume.experience:
        lines += 2
        for e in resume.experience:
            lines += 1.4 + sum(n(b.text, LINE_CHARS - 4) for b in e.bullets)
    if resume.projects:
        lines += 2
        for p in resume.projects:
            lines += 1.2 + sum(n(b.text, LINE_CHARS - 4) for b in p.bullets)
    if resume.education:
        lines += 2 + sum(1.2 + len(e.details) for e in resume.education)
    if resume.certifications:
        lines += 2 + len(resume.certifications)
    return lines
