"""Resume build service — bridges the FastAPI layer with the core pipeline engine.

Each build runs in a thread pool (run_in_executor) so it doesn't block the
event loop, and progress is reported through an asyncio.Queue so the SSE
endpoint can stream events line by line.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.models import User
from ..config import get_settings
from ..history.models import ResumeHistory
from ..keys.service import decrypt_key, get_active_key, get_key_by_id
from ..profile.service import get_or_create_profile
from ..storage.s3 import upload_file

# Add the src directory to path so we can import the core engine
for _candidate in (Path(__file__).resolve().parents[3] / "src", Path(__file__).resolve().parents[2] / "src"):
    if _candidate.exists() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))
        break

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="resume_build")


# ── LLM client resolver ───────────────────────────────────────────────────────

async def _resolve_llm_env(
    user: User,
    db: AsyncSession,
    selected_key_id: str | None = None,
    requested_model: str | None = None,
) -> tuple[dict[str, str], str | None, str | None]:
    """
    Returns (env_overrides, provider_used, model_used).
    env_overrides is a dict of env vars to temporarily set so the core engine
    picks up the right key — the engine reads from os.environ.
    """
    # If the user explicitly chose no AI key (empty string or None):
    if not selected_key_id or selected_key_id == "none":
        return {}, None, None

    settings = get_settings()
    active = None
    try:
        kid = uuid.UUID(str(selected_key_id))
        active = await get_key_by_id(kid, user.id, db)
    except Exception:
        active = None

    if not active:
        active = await get_active_key(user.id, db)

    if active:
        try:
            raw_key = decrypt_key(active)
            key_env_map = {
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
                "gemini": "GEMINI_API_KEY",
            }
            env = {
                key_env_map.get(active.provider, "OPENAI_API_KEY"): raw_key,
                "RESUME_PROVIDER": active.provider,
            }
            model_to_use = requested_model or active.model_strong or active.model_fast
            if model_to_use:
                env["RESUME_FAST_MODEL"] = model_to_use
                env["RESUME_STRONG_MODEL"] = model_to_use
            return env, active.provider, model_to_use
        except Exception:
            # Corrupted key or encryption key mismatch - fallback gracefully to heuristic
            return {}, None, None

    # No key — heuristic mode
    return {}, None, None


# ── Profile → profile.json ────────────────────────────────────────────────────

def _normalize_skills(raw_skills) -> list[dict]:
    skills_list: list[dict] = []
    if isinstance(raw_skills, dict):
        for category, items in raw_skills.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        skills_list.append(item)
                    elif isinstance(item, str) and item.strip():
                        skills_list.append({
                            "name": item.strip(),
                            "category": str(category).title(),
                            "aliases": [],
                            "years": None,
                            "level": "working",
                        })
    elif isinstance(raw_skills, list):
        for item in raw_skills:
            if isinstance(item, dict):
                skills_list.append(item)
            elif isinstance(item, str) and item.strip():
                skills_list.append({
                    "name": item.strip(),
                    "category": "Other",
                    "aliases": [],
                    "years": None,
                    "level": "working",
                })
    return skills_list


def _normalize_links(raw_links) -> list[dict]:
    out: list[dict] = []
    if isinstance(raw_links, list):
        for item in raw_links:
            if isinstance(item, dict) and "url" in item:
                out.append({"label": item.get("label") or "Link", "url": item.get("url") or ""})
            elif isinstance(item, str) and item.strip():
                out.append({"label": "Link", "url": item.strip()})
    return out


def _profile_orm_to_dict(profile) -> dict:
    """Convert the ORM Profile model to the dict format the core engine expects."""
    return {
        "basics": {
            "name": profile.full_name or "Resume Candidate",
            "email": profile.email or "",
            "phone": profile.phone or "",
            "location": profile.location or "",
            "links": _normalize_links(profile.links),
        },
        "preferences": {
            "career_stage": profile.career_stage or "experienced",
            "max_pages": profile.max_pages or 1,
            "date_format": profile.date_format or "MMM YYYY",
            "paper_size": profile.paper_size or "Letter",
        },
        "summary_facts": profile.summary_facts or [],
        "skills": _normalize_skills(profile.skills),
        "experience": profile.experience or [],
        "projects": profile.projects or [],
        "education": profile.education or [],
        "certifications": profile.certifications or [],
        "never_claim": profile.never_claim or [],
    }


# ── Blocking build (runs in thread) ──────────────────────────────────────────

def _run_build_sync(
    profile_dict: dict,
    jd_text: str,
    env_overrides: dict[str, str],
    make_pdf: bool,
    progress_queue,   # queue.Queue (sync version)
    tmp_dir: str,
):
    """
    Pure synchronous build — called in thread pool.
    Uses the core engine's build() function after writing a temp profile.json.
    Reports progress via a sync queue.
    """
    import queue as _queue
    
    old_env = {}
    try:
        # Apply env overrides
        for k, v in env_overrides.items():
            old_env[k] = os.environ.get(k)
            os.environ[k] = v

        def emit(msg: str):
            progress_queue.put(("progress", msg))

        emit("Loading profile…")
        # Write temp profile JSON
        profile_path = Path(tmp_dir) / "profile.json"
        profile_path.write_text(json.dumps(profile_dict), encoding="utf-8")

        emit("Parsing job description…")
        from resume_builder.pipeline import build, load_profile
        profile = load_profile(profile_path)

        emit("Matching skills to JD…")
        result = build(
            profile_path=profile_path,
            jd_source=jd_text,
            out_root=tmp_dir,
            make_pdf=make_pdf,
        )

        emit("Uploading resume…")
        progress_queue.put(("result", result))

    except Exception as e:
        progress_queue.put(("error", str(e)))
    finally:
        for k, old_v in old_env.items():
            if old_v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old_v


def resume_to_markdown(resume, target_title: str | None = None, target_company: str | None = None) -> str:
    """Format the generated Resume model into clean, professional Markdown for preview & export."""
    lines = []
    # Header
    name = getattr(resume.basics, "name", "") or "Resume Candidate"
    lines.append(f"# {name}\n")

    contacts = []
    if getattr(resume.basics, "email", None):
        contacts.append(resume.basics.email)
    if getattr(resume.basics, "phone", None):
        contacts.append(resume.basics.phone)
    if getattr(resume.basics, "location", None):
        contacts.append(resume.basics.location)
    for link in getattr(resume.basics, "links", []):
        url = getattr(link, "url", "") if hasattr(link, "url") else link.get("url", "")
        label = getattr(link, "label", "") if hasattr(link, "label") else link.get("label", "Link")
        if url:
            contacts.append(f"[{label}]({url})")
    if contacts:
        lines.append(" | ".join(contacts))
        lines.append("")

    t_title = target_title.strip() if target_title else ""
    t_comp = target_company.strip() if target_company and target_company.lower() != "none" else ""
    if t_title and t_comp:
        lines.append(f"**Target Role:** {t_title} · **Target Company:** {t_comp}\n")
    elif t_title:
        lines.append(f"**Target Role:** {t_title}\n")

    # Summary
    if getattr(resume, "summary", None):
        lines.append("## Professional Summary")
        lines.append(resume.summary.strip())
        lines.append("")

    # Skills
    if getattr(resume, "skills", None):
        lines.append("## Core Skills")
        for group in resume.skills:
            g_skills = getattr(group, "skills", [])
            g_cat = getattr(group, "category", "Skills")
            if g_skills:
                lines.append(f"- **{g_cat}**: {', '.join(g_skills)}")
        lines.append("")

    # Experience
    if getattr(resume, "experience", None):
        lines.append("## Work Experience")
        for exp in resume.experience:
            dates = f"{exp.start} – {exp.end or 'Present'}"
            loc = f" · {exp.location}" if exp.location else ""
            lines.append(f"### {exp.title} | {exp.company}{loc}")
            lines.append(f"*{dates}*\n")
            for b in exp.bullets:
                lines.append(f"- {b.text}")
            lines.append("")

    # Projects
    if getattr(resume, "projects", None):
        lines.append("## Key Projects")
        for proj in resume.projects:
            url_part = f" — [Project Link]({proj.url})" if proj.url else ""
            lines.append(f"### {proj.name}{url_part}")
            for b in proj.bullets:
                lines.append(f"- {b.text}")
            lines.append("")

    # Education
    if getattr(resume, "education", None):
        lines.append("## Education")
        for edu in resume.education:
            dates = f"{edu.start} – {edu.end or 'Present'}" if edu.start or edu.end else ""
            lines.append(f"### {edu.degree} · {edu.institution}")
            if dates:
                lines.append(f"*{dates}*\n")
            for d in getattr(edu, "details", []):
                lines.append(f"- {d}")
            lines.append("")

    # Certifications
    if getattr(resume, "certifications", None):
        lines.append("## Certifications")
        for cert in resume.certifications:
            issuer = f" ({cert.issuer})" if cert.issuer else ""
            date_str = f" · {cert.date}" if cert.date else ""
            lines.append(f"- **{cert.name}**{issuer}{date_str}")
        lines.append("")

    return "\n".join(lines).strip()


# ── Async streaming build ─────────────────────────────────────────────────────

async def build_resume_stream(
    user: User,
    jd_text: str,
    make_pdf: bool,
    db: AsyncSession,
    selected_key_id: str | None = None,
    model: str | None = None,
) -> AsyncGenerator[dict, None]:
    """
    AsyncGenerator that yields SSE-compatible dicts:
      { "event": "progress" | "done" | "error", "data": str | dict }
    """
    import queue as _queue

    env_overrides, provider_used, model_used = await _resolve_llm_env(
        user, db, selected_key_id=selected_key_id, requested_model=model
    )
    profile_orm = await get_or_create_profile(user.id, db)
    profile_dict = _profile_orm_to_dict(profile_orm)

    sync_q: _queue.Queue = _queue.Queue()
    loop = asyncio.get_event_loop()
    history_id = uuid.uuid4()

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Start the blocking build in the thread pool
        future = loop.run_in_executor(
            _executor,
            _run_build_sync,
            profile_dict,
            jd_text,
            env_overrides,
            make_pdf,
            sync_q,
            tmp_dir,
        )

        # Poll the sync queue and yield events
        result = None
        error = None
        while True:
            try:
                event_type, data = sync_q.get(timeout=0.1)
            except _queue.Empty:
                if future.done():
                    break
                await asyncio.sleep(0.05)
                continue

            if event_type == "progress":
                yield {"event": "progress", "data": data}
                await asyncio.sleep(0)
            elif event_type == "result":
                result = data
                break
            elif event_type == "error":
                error = data
                break

        # Ensure the future is done
        try:
            await asyncio.wait_for(asyncio.shield(future), timeout=5.0)
        except (asyncio.TimeoutError, Exception):
            pass

        if error:
            yield {"event": "error", "data": {"message": error}}
            return

        if result is None:
            yield {"event": "error", "data": {"message": "Build failed with no result"}}
            return

        # Upload to S3
        yield {"event": "progress", "data": "Uploading files to storage…"}
        s3_key_docx = s3_key_pdf = None
        try:
            if result.docx and result.docx.exists():
                s3_key_docx = f"resumes/{user.id}/{history_id}/resume.docx"
                upload_file(result.docx, s3_key_docx)
            if result.pdf and result.pdf.exists():
                s3_key_pdf = f"resumes/{user.id}/{history_id}/resume.pdf"
                upload_file(result.pdf, s3_key_pdf)
        except Exception as e:
            yield {"event": "progress", "data": f"Warning: S3 upload failed — {e}"}

        # Write history row
        import json as _json
        notes_json = _json.dumps(result.notes) if result.notes else None
        score_val = None
        if hasattr(result, "ats") and result.ats:
            if callable(getattr(result.ats, "score", None)):
                try:
                    score_val = int(round(result.ats.score()))
                except Exception:
                    score_val = 85
            elif isinstance(getattr(result.ats, "score", None), (int, float)):
                score_val = int(round(result.ats.score))

        md_content = (
            resume_to_markdown(
                result.resume,
                target_title=result.jd.title,
                target_company=result.jd.company,
            )
            if hasattr(result, "resume") and result.resume
            else ""
        )
        matched_kw = (
            list(dict.fromkeys(result.ats.matched_must + result.ats.matched_nice))
            if hasattr(result, "ats") and result.ats
            else []
        )
        missing_kw = (
            list(dict.fromkeys(result.ats.missing_must + result.ats.missing_nice))
            if hasattr(result, "ats") and result.ats
            else []
        )

        history_row = ResumeHistory(
            id=history_id,
            user_id=user.id,
            jd_title=result.jd.title or None,
            jd_company=result.jd.company or None,
            jd_text=jd_text,
            s3_key_docx=s3_key_docx,
            s3_key_pdf=s3_key_pdf,
            ats_score=score_val,
            model_used=model_used,
            provider_used=provider_used,
            notes=notes_json,
            markdown=md_content,
        )
        db.add(history_row)
        await db.commit()

        yield {
            "event": "done",
            "data": {
                "history_id": str(history_id),
                "ats_score": history_row.ats_score,
                "jd_title": history_row.jd_title,
                "jd_company": history_row.jd_company,
                "has_docx": bool(s3_key_docx),
                "has_pdf": bool(s3_key_pdf),
                "s3_key_docx": s3_key_docx,
                "s3_key_pdf": s3_key_pdf,
                "markdown": md_content,
                "matched_keywords": matched_kw,
                "missing_keywords": missing_kw,
                "notes": result.notes,
            },
        }
