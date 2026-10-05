"""Glue: ingest -> parse JD -> select -> tailor -> validate -> render -> ATS check -> report."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .ats_check import ATSReport, check_file
from .ingest import load_jd_text
from .jd_parser import parse_jd
from .llm import (
    LLMClient, LLMUnavailable, available_providers, describe_active, get_client, load_dotenv_if_present,
)
from .matcher import Selection, display_skill, select
from .models import JD, Profile, Resume, ResumeBullet, ResumeExperience, ResumeProject, SkillGroup
from .render import PdfError, docx_to_pdf, page_count, render_docx, resume_to_markdown
from .report import build_report
from .textutil import SkillIndex, slugify, today
from .validator import validate
from .writer import base_resume, tailor


class ProfileError(RuntimeError):
    pass


@dataclass
class BuildResult:
    folder: Path
    resume: Resume
    jd: JD
    selection: Selection
    ats: ATSReport
    notes: list[str] = field(default_factory=list)
    docx: Path | None = None
    pdf: Path | None = None


# ------------------------------------------------------------------ profile
def load_profile(path: str | Path) -> Profile:
    p = Path(path)
    if not p.exists():
        raise ProfileError(f"{p} not found. Run `resume init` to create a starter profile.")
    try:
        profile = Profile.model_validate(json.loads(p.read_text(encoding="utf-8")))
    except json.JSONDecodeError as e:
        raise ProfileError(f"{p} is not valid JSON: {e}") from e
    except Exception as e:  # pydantic.ValidationError
        raise ProfileError(f"{p} failed schema validation:\n{e}") from e
    problems = profile.check_integrity()
    if problems:
        raise ProfileError("profile.json problems:\n" + "\n".join(f"  - {x}" for x in problems))
    return profile


def full_resume(profile: Profile) -> Resume:
    """Phase-1 helper: the ENTIRE profile, no JD, no AI. Used to test the renderer."""
    pr = profile.preferences
    cats: dict[str, list[str]] = {}
    for s in profile.skills:
        if not SkillIndex(profile).is_blocked(s.name):
            cats.setdefault(s.category, []).append(display_skill(s))
    return Resume(
        basics=profile.basics, career_stage=pr.career_stage, date_format=pr.date_format,
        paper_size=pr.paper_size, max_pages=pr.max_pages,
        summary=" ".join(f.strip().rstrip(".") + "." for f in profile.summary_facts),
        skills=[SkillGroup(category=c, skills=v) for c, v in cats.items()],
        experience=[
            ResumeExperience(
                id=e.id, company=e.company, title=e.title, location=e.location, start=e.start, end=e.end,
                bullets=[ResumeBullet(source_id=b.id, text=b.text) for b in e.bullets],
            )
            for e in profile.experience
        ],
        projects=[
            ResumeProject(id=p.id, name=p.name, url=p.url,
                          bullets=[ResumeBullet(source_id=b.id, text=b.text) for b in p.bullets])
            for p in profile.projects
        ],
        education=profile.education, certifications=profile.certifications,
    )


# ------------------------------------------------------------------ build
def resolve_client(use_llm: bool | None, notes: list[str]) -> LLMClient | None:
    """use_llm: False = never, True = required, None = use an LLM if any provider key is configured."""
    load_dotenv_if_present()
    if use_llm is False:
        return None
    if use_llm is None and not os.environ.get("RESUME_PROVIDER") and not available_providers():
        notes.append("No API key set (ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY): ran without the LLM "
                     "(heuristic JD parsing, no rewording).")
        return None
    try:
        client = get_client()
    except LLMUnavailable as e:
        if use_llm:
            raise
        notes.append(f"LLM unavailable ({e}): ran without it.")
        return None
    notes.append(f"LLM provider: {describe_active()}")
    return client


def _unique_dir(root: Path, name: str) -> Path:
    d = root / name
    n = 2
    while d.exists():
        d = root / f"{name}-{n}"
        n += 1
    d.mkdir(parents=True)
    return d


def _fit_to_pages(resume: Resume, docx: Path, pdf: Path | None, notes: list[str]) -> Path | None:
    """If the real PDF is longer than max_pages, drop the weakest bullets (oldest roles first) and re-render."""
    if pdf is None:
        return None
    dropped = 0
    for _ in range(12):
        if page_count(pdf) <= resume.max_pages:
            break
        victim = next((e for e in reversed(resume.experience) if len(e.bullets) > 2), None) or next(
            (p for p in reversed(resume.projects) if len(p.bullets) > 1), None
        )
        if victim is None:
            notes.append(f"Still {page_count(pdf)} pages after trimming; shorten profile bullets or raise max_pages.")
            break
        victim.bullets.pop()
        dropped += 1
        render_docx(resume, docx)
        pdf = docx_to_pdf(docx, pdf)
    if dropped:
        notes.append(f"Dropped {dropped} lowest-priority bullet(s) to fit {resume.max_pages} page(s).")
    return pdf


def build(
    profile_path: str | Path,
    jd_source: str | None,
    *,
    use_llm: bool | None = None,
    out_root: str | Path = "output",
    client: LLMClient | None = None,
    company: str | None = None,
    title: str | None = None,
    make_pdf: bool = True,
) -> BuildResult:
    notes: list[str] = []
    profile = load_profile(profile_path)
    jd_text = load_jd_text(jd_source)
    if client is None:
        client = resolve_client(use_llm, notes)

    jd = parse_jd(jd_text, profile, client)
    if company:
        jd.company = company
    if title:
        jd.title = title

    sel = select(profile, jd)
    resume, writer_notes = tailor(profile, jd, sel, client)
    notes += writer_notes

    folder = _unique_dir(Path(out_root), f"{today()}_{slugify(jd.company, 'company')}_{slugify(jd.title, 'role')}")
    docx = render_docx(resume, folder / "resume.docx")
    pdf: Path | None = None
    if make_pdf:
        try:
            pdf = docx_to_pdf(docx, folder / "resume.pdf")
            pdf = _fit_to_pages(resume, docx, pdf, notes)
        except PdfError as e:
            notes.append(str(e))

    errors = validate(resume, profile, jd, sel)
    if errors:
        notes += [f"validator: {e}" for e in errors]
    ats = check_file(docx, resume=resume, jd=jd, idx=SkillIndex(profile), max_pages=resume.max_pages, pdf_path=pdf)

    (folder / "resume.json").write_text(json.dumps(resume.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
    (folder / "resume.md").write_text(
        resume_to_markdown(resume, target_title=jd.title, target_company=jd.company) + "\n",
        encoding="utf-8",
    )
    (folder / "jd.json").write_text(json.dumps(jd.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
    (folder / "jd_raw.txt").write_text(jd_text, encoding="utf-8")
    (folder / "resume.txt").write_text(ats.text + "\n", encoding="utf-8")
    (folder / "report.md").write_text(build_report(jd, ats, sel, notes, resume=resume), encoding="utf-8")

    # submission copies named FirstName_LastName_Company_Role
    stem = "_".join(re.sub(r"[^A-Za-z0-9]+", "", w) for w in [*profile.basics.name.split(), jd.company or "Company", *(jd.title or "Role").split()[:4]] if w)
    for src in (docx, pdf):
        if src is not None:
            (folder / f"{stem}{src.suffix}").write_bytes(src.read_bytes())

    return BuildResult(folder=folder, resume=resume, jd=jd, selection=sel, ats=ats, notes=notes, docx=docx, pdf=pdf)
