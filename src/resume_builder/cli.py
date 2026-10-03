"""CLI: `resume build --jd job.txt`"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

import typer

from . import pipeline
from .ats_check import check_file
from .ingest import IngestError, load_jd_text
from .jd_parser import parse_jd
from .llm import LLMUnavailable
from .matcher import select
from .models import JD
from .render import PdfError, docx_to_pdf, render_docx
from .textutil import SkillIndex

app = typer.Typer(add_completion=False, help="Personal AI resume builder: truthful, ATS-safe, tailored per job.")
PROFILE_OPT = typer.Option("data/profile.json", "--profile", "-p", help="Path to profile.json")


@app.callback()
def main(
    provider: Optional[str] = typer.Option(
        None, "--provider", help="LLM provider: claude, openai (chatgpt) or gemini. Default: auto-detect from your API keys."
    ),
) -> None:
    """Personal AI resume builder."""
    if provider:
        import os
        from .llm import LLMUnavailable, normalize_provider

        try:
            os.environ["RESUME_PROVIDER"] = normalize_provider(provider)
        except LLMUnavailable as e:
            typer.secho(str(e), fg=typer.colors.RED, err=True)
            raise typer.Exit(1)


def _fail(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


@app.command()
def init(force: bool = typer.Option(False, "--force", help="Overwrite an existing profile")) -> None:
    """Create data/profile.json from the bundled example."""
    dest = Path("data/profile.json")
    example = Path("data/profile.example.json")
    if not example.exists():
        _fail("data/profile.example.json not found (run from the project root).")
    if dest.exists() and not force:
        _fail("data/profile.json already exists (use --force to overwrite).")
    dest.parent.mkdir(exist_ok=True)
    shutil.copy(example, dest)
    typer.echo("Created data/profile.json. Replace the sample content with your real facts, then run `resume validate-profile`.")


@app.command("validate-profile")
def validate_profile(profile: Path = PROFILE_OPT) -> None:
    """Check profile.json against the schema and sanity rules."""
    try:
        p = pipeline.load_profile(profile)
    except pipeline.ProfileError as e:
        _fail(str(e))
    n_b = len(p.all_bullets())
    typer.echo(f"OK: {len(p.experience)} roles, {n_b} bullets, {len(p.skills)} skills, {len(p.projects)} projects.")
    no_metric = [bid for bid, b in p.all_bullets().items() if not b.metrics]
    if no_metric:
        typer.echo(f"Tip: {len(no_metric)} bullet(s) have no metrics (tailoring works best with real numbers): {', '.join(no_metric[:8])}")


@app.command()
def quantify(profile: Path = PROFILE_OPT) -> None:
    """List every profile bullet that has no number, so you can add real metrics (recruiters and ATS checkers reward them)."""
    from .matcher import unquantified_bullets

    try:
        p = pipeline.load_profile(profile)
    except pipeline.ProfileError as e:
        _fail(str(e))
    weak = unquantified_bullets(p)
    total = len(p.all_bullets())
    typer.echo(f"{len(weak)} of {total} bullets have no number. Edit them in profile.json (text + metrics), only with true figures:\n")
    for b in weak:
        typer.echo(f"  {b.id}: {b.text}")


@app.command()
def render(
    profile: Path = PROFILE_OPT,
    out: Path = typer.Option("output/full_profile", "--out", "-o", help="Output folder"),
    pdf: bool = typer.Option(True, "--pdf/--no-pdf"),
) -> None:
    """Phase 1: render the ENTIRE profile to DOCX (+PDF), no AI, no tailoring."""
    try:
        p = pipeline.load_profile(profile)
    except pipeline.ProfileError as e:
        _fail(str(e))
    r = pipeline.full_resume(p)
    out.mkdir(parents=True, exist_ok=True)
    docx = render_docx(r, out / "resume.docx")
    typer.echo(f"Wrote {docx}")
    if pdf:
        try:
            typer.echo(f"Wrote {docx_to_pdf(docx, out / 'resume.pdf')}")
        except PdfError as e:
            typer.secho(str(e), fg=typer.colors.YELLOW)
    rep = check_file(docx, resume=r, idx=SkillIndex(p), max_pages=p.preferences.max_pages, pdf_path=out / "resume.pdf")
    (out / "resume.txt").write_text(rep.text + "\n", encoding="utf-8")
    typer.echo(rep.summary_line())


@app.command()
def check(
    file: Path = typer.Argument(..., help="A .docx or .pdf resume"),
    jd: Optional[str] = typer.Option(None, "--jd", help="Job description (file/URL/text) for keyword coverage"),
    max_pages: int = typer.Option(1, "--max-pages"),
    profile: Optional[Path] = typer.Option(None, "--profile", "-p", help="Use profile aliases when matching keywords"),
) -> None:
    """Phase 2: run the ATS checker on ANY resume file."""
    if not file.exists():
        _fail(f"{file} not found")
    prof = pipeline.load_profile(profile) if profile else None
    jd_obj: JD | None = None
    if jd:
        try:
            text = load_jd_text(jd)
        except IngestError as e:
            _fail(str(e))
        if prof is None:
            from .models import Basics, Profile
            prof_for_parse = Profile(basics=Basics(name="x", email="x@x.x"))
        else:
            prof_for_parse = prof
        jd_obj = parse_jd(text, prof_for_parse, None)
    pdf_sibling = file.with_suffix(".pdf") if file.suffix.lower() == ".docx" else None
    rep = check_file(file, jd=jd_obj, idx=SkillIndex(prof) if prof else None, max_pages=max_pages, pdf_path=pdf_sibling)
    typer.echo(rep.summary_line())
    from .ats_check import WEIGHTS

    for comp in WEIGHTS:
        if comp in rep.not_applicable:
            continue
        typer.echo(f"\n{comp}: {rep.score(comp):.1f}/{WEIGHTS[comp]}")
        for c in rep.components.get(comp, []):
            flag = "ok  " if c.earned >= 0.999 else "FAIL" if c.earned == 0 else "part"
            typer.echo(f"  [{flag}] {c.name}" + (f" - {c.detail}" if c.detail else ""))
    for w in rep.warnings:
        typer.echo(f"warning: {w}")


@app.command("parse-jd")
def parse_jd_cmd(
    jd: Optional[str] = typer.Option(None, "--jd", help="File, URL, or text ('-' for stdin)"),
    profile: Path = PROFILE_OPT,
    llm: Optional[bool] = typer.Option(None, "--llm/--no-llm"),
) -> None:
    """Phase 3: job text/URL -> jd.json (printed)."""
    try:
        p = pipeline.load_profile(profile)
        text = load_jd_text(jd)
        notes: list[str] = []
        client = pipeline.resolve_client(llm, notes)
    except (pipeline.ProfileError, IngestError, LLMUnavailable) as e:
        _fail(str(e))
    for n in notes:
        typer.secho(n, fg=typer.colors.YELLOW, err=True)
    typer.echo(json.dumps(parse_jd(text, p, client).model_dump(), indent=2, ensure_ascii=False))


@app.command()
def match(
    jd: Optional[str] = typer.Option(None, "--jd"),
    profile: Path = PROFILE_OPT,
    llm: Optional[bool] = typer.Option(None, "--llm/--no-llm"),
) -> None:
    """Phase 4: show which bullets/skills would be picked, with scores and gaps (no writing)."""
    try:
        p = pipeline.load_profile(profile)
        text = load_jd_text(jd)
        notes: list[str] = []
        client = pipeline.resolve_client(llm, notes)
    except (pipeline.ProfileError, IngestError, LLMUnavailable) as e:
        _fail(str(e))
    j = parse_jd(text, p, client)
    sel = select(p, j)
    typer.echo(f"Job: {j.title} @ {j.company or '?'}   must-have: {', '.join(j.must_have) or '-'}")
    for e, bs in sel.experience:
        typer.echo(f"\n{e.title} · {e.company}")
        for b in bs:
            typer.echo(f"  {sel.scores[b.id]:5.1f}  {b.id}: {b.text[:90]}")
    for pr, bs in sel.projects:
        typer.echo(f"\nProject: {pr.name}")
        for b in bs:
            typer.echo(f"  {sel.scores[b.id]:5.1f}  {b.id}: {b.text[:90]}")
    typer.echo("\nSkills: " + " | ".join(f"{g.category}: {', '.join(g.skills)}" for g in sel.skill_groups))
    typer.echo(f"Matched must-have: {', '.join(sel.matched_must) or '-'}")
    typer.echo(f"Gaps (must): {', '.join(sel.gaps_must) or '-'}   Gaps (nice): {', '.join(sel.gaps_nice) or '-'}")


@app.command()
def build(
    jd: Optional[str] = typer.Option(None, "--jd", "-j", help="Job description: file, URL, or text ('-' for stdin)"),
    profile: Path = PROFILE_OPT,
    out: Path = typer.Option("output", "--out", "-o", help="Root output folder"),
    company: Optional[str] = typer.Option(None, "--company", help="Override the company name"),
    title: Optional[str] = typer.Option(None, "--title", help="Override the job title"),
    llm: Optional[bool] = typer.Option(None, "--llm/--no-llm", help="Default: use the LLM when ANTHROPIC_API_KEY is set"),
    pdf: bool = typer.Option(True, "--pdf/--no-pdf"),
) -> None:
    """Build a tailored resume + report for one job."""
    try:
        res = pipeline.build(profile, jd, use_llm=llm, out_root=out, company=company, title=title, make_pdf=pdf)
    except (pipeline.ProfileError, IngestError, LLMUnavailable) as e:
        _fail(str(e))
    typer.echo(f"\n{res.jd.title or 'Job'} @ {res.jd.company or '?'}")
    typer.echo(res.ats.summary_line())
    if res.ats.missing_must:
        typer.echo("Missing must-have: " + ", ".join(res.ats.missing_must))
    for n in res.notes:
        typer.secho(f"note: {n}", fg=typer.colors.YELLOW)
    typer.echo(f"\nSaved to {res.folder}/")


if __name__ == "__main__":  # pragma: no cover
    app()
