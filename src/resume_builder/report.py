"""Step 8: human-readable report.md"""
from __future__ import annotations

from .ats_check import WEIGHTS, ATSReport
from .matcher import Selection
import re

from .models import JD, Resume


def build_report(
    jd: JD, rep: ATSReport, sel: Selection, notes: list[str], *, valid_errors: list[str] | None = None,
    resume: Resume | None = None
) -> str:
    L: list[str] = []
    L.append(f"# Match report: {jd.company or 'Unknown company'}, {jd.title or 'Unknown role'}")
    L.append("")
    L.append(f"**{rep.summary_line()}**")
    if rep.pages is not None:
        L.append(f"Pages: {rep.pages}")
    L.append("")
    L.append(f"- Matched must-have: {', '.join(rep.matched_must) or '(none)'}")
    L.append(f"- Missing must-have: {', '.join(rep.missing_must) or '(none)'}")
    if rep.matched_nice or rep.missing_nice:
        L.append(f"- Matched nice-to-have: {', '.join(rep.matched_nice) or '(none)'}")
    L.append("")
    L.append("## Gaps (JD asks, profile does not support; NOT added to the resume)")
    gaps = [*sel.gaps_must, *[g for g in sel.gaps_nice if g not in sel.gaps_must]]
    if gaps:
        for g in gaps:
            tag = " (in never_claim)" if g in sel.blocked else ""
            kind = "must-have" if g in sel.gaps_must else "nice-to-have"
            L.append(f"- {g}: {kind}{tag}. Add it to profile.json only if it is true.")
    else:
        L.append("- none")
    L.append("")
    L.append("## Score breakdown")
    for comp in WEIGHTS:
        if comp in rep.not_applicable:
            L.append(f"### {comp}: n/a ({rep.not_applicable[comp]})")
            continue
        L.append(f"### {comp}: {rep.score(comp):.1f}/{WEIGHTS[comp]}")
        for c in rep.components.get(comp, []):
            mark = "pass" if c.earned >= 0.999 else ("partial" if c.earned > 0 else "FAIL")
            L.append(f"- [{mark}] {c.name}" + (f": {c.detail}" if c.detail else ""))
    L.append("")
    if rep.warnings or notes or valid_errors:
        L.append("## Warnings and notes")
        for w in [*rep.warnings, *notes, *(valid_errors or [])]:
            L.append(f"- {w}")
        L.append("")
    if resume is not None:
        flat = [(e.company, b) for e in resume.experience for b in e.bullets] + [(p.name, b) for p in resume.projects for b in p.bullets]
        weak = [(w, b) for w, b in flat if not re.search(r"\d", b.text)]
        if weak:
            L.append(f"## Bullets with no number ({len(weak)} of {len(flat)})")
            L.append("Add a real metric to these in profile.json if you have one (users, %, time saved, volume, team size). Never guess.")
            for w, b in weak:
                L.append(f"- {b.source_id} ({w}): {b.text}")
            L.append("")
    L.append("## Selected bullets (score)")
    for e, bs in sel.experience:
        for b in bs:
            L.append(f"- {b.id} ({sel.scores.get(b.id, 0):g}) {e.company}")
    for p, bs in sel.projects:
        for b in bs:
            L.append(f"- {b.id} ({sel.scores.get(b.id, 0):g}) project: {p.name}")
    L.append("")
    if sel.unused_bullets:
        L.append("## Bullets not selected for this job")
        L.append(", ".join(sel.unused_bullets))
        L.append("")
    L.append(
        "> The score is a proxy for parse quality and relevance. It is a diagnostic, "
        "not a promise about any employer's ATS. See `resume.txt` for the plain-text test."
    )
    return "\n".join(L) + "\n"
