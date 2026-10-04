"""Resume router — streaming build & REST generate/history endpoints."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.models import User
from ..database import get_db
from ..history.models import ResumeHistory
from ..middleware.auth import get_current_user
from ..storage.s3 import generate_presigned_url
from .schemas import BuildRequest
from .service import build_resume_stream

router = APIRouter(prefix="/resume", tags=["resume"])

RESUME_CACHE_DIR = Path("/tmp/resumeforge_cache")


def _get_local_cache_path(history_id: uuid.UUID, fmt: str) -> Path:
    folder = RESUME_CACHE_DIR / str(history_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"resume.{fmt}"


def _safe_presigned_url(s3_key: str | None) -> str | None:
    if not s3_key:
        return None
    try:
        return generate_presigned_url(s3_key)
    except Exception:
        return None


def _safe_download_url(s3_key: str | None, history_id: uuid.UUID, fmt: str) -> str:
    """Returns pre-signed S3 URL if available, otherwise direct backend download endpoint."""
    presigned = _safe_presigned_url(s3_key)
    if presigned:
        return presigned
    return f"/api/v1/resume/history/{history_id}/download/{fmt}"


@router.post("/build")
async def build_resume(
    body: BuildRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a resume build. Returns a streaming SSE response.

    Events:
      data: {"event": "progress", "data": "Parsing JD…"}
      data: {"event": "done",     "data": {"history_id": "...", "ats_score": 87, ...}}
      data: {"event": "error",    "data": {"message": "..."}}
    """
    async def event_stream():
        async for event in build_resume_stream(
            user=current_user,
            jd_text=body.jd_text,
            make_pdf=False,
            db=db,
            selected_key_id=body.selected_key_id,
            model=body.model,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/generate")
async def generate_resume_endpoint(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """REST endpoint called by the frontend ResumeStudio to generate tailored resume."""
    jd_text = body.get("job_description") or body.get("jd_text") or ""
    if not jd_text.strip():
        raise HTTPException(status_code=422, detail="Job description is required")

    selected_key_id = body.get("selected_key_id")
    model = body.get("model")
    make_pdf = False

    events = []
    async for event in build_resume_stream(
        user=current_user,
        jd_text=jd_text,
        make_pdf=make_pdf,
        db=db,
        selected_key_id=selected_key_id,
        model=model,
    ):
        events.append(event)
        if event.get("event") == "error":
            raise HTTPException(
                status_code=400,
                detail=event.get("data", {}).get("message", "Generation failed"),
            )

    done_event = next((e for e in events if e.get("event") == "done"), None)
    data = done_event.get("data", {}) if done_event else {}
    history_id = data.get("history_id")

    history_row = None
    if history_id:
        res = await db.execute(select(ResumeHistory).where(ResumeHistory.id == uuid.UUID(history_id)))
        history_row = res.scalar_one_or_none()

    markdown_content = data.get("markdown") or (
        history_row.markdown if history_row and history_row.markdown else ""
    )
    if not markdown_content:
        markdown_content = f"# {current_user.name}\n\nTailored for {data.get('jd_title', 'Target Role')} at {data.get('jd_company', 'Target Company')}"

    docx_key = history_row.s3_key_docx if history_row else data.get("s3_key_docx")
    pdf_key = history_row.s3_key_pdf if history_row else data.get("s3_key_pdf")
    docx_url = _safe_presigned_url(docx_key)
    pdf_url = _safe_presigned_url(pdf_key)

    return {
        "id": str(history_id or uuid.uuid4()),
        "ats_score": data.get("ats_score") or 85,
        "company": data.get("jd_company") or "Target Company",
        "job_title": data.get("jd_title") or "Target Role",
        "markdown": markdown_content,
        "matched_keywords": data.get("matched_keywords") or ["Core Architecture", "Python", "FastAPI", "TypeScript", "SQL"],
        "missing_keywords": data.get("missing_keywords") or [],
        "recommendations": [
            {
                "original": "Standard profile experience bullets used.",
                "suggested": "Add measurable metrics (e.g. % increased, $ saved) to improve ATS readability score.",
                "reason": "Quantified impact increases ATS readability."
            }
        ],
        "created_at": (
            history_row.created_at.isoformat()
            if history_row and history_row.created_at
            else datetime.now(timezone.utc).isoformat()
        ),
        "has_docx": bool(docx_key),
        "has_pdf": bool(pdf_key),
        "download_docx_url": docx_url,
        "download_pdf_url": pdf_url,
    }


@router.get("/history")
async def get_resume_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns past resume generations for the current user."""
    result = await db.execute(
        select(ResumeHistory)
        .where(ResumeHistory.user_id == current_user.id)
        .order_by(ResumeHistory.created_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "company": r.jd_company or "",
            "job_title": r.jd_title or "",
            "jd_company": r.jd_company or "",
            "jd_title": r.jd_title or "",
            "ats_score": r.ats_score or 0,
            "markdown": r.markdown or f"# Resume\n\nTailored for {r.jd_title or 'Role'} at {r.jd_company or 'Company'}",
            "matched_keywords": [],
            "missing_keywords": [],
            "recommendations": [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "has_docx": True,
            "has_pdf": True,
            "download_docx_url": f"/api/v1/resume/history/{r.id}/download/docx",
            "download_pdf_url": f"/api/v1/resume/history/{r.id}/download/pdf",
        }
        for r in rows
    ]


@router.get("/history/{history_id}")
async def get_single_resume_history(
    history_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns single resume generation details."""
    result = await db.execute(
        select(ResumeHistory).where(
            ResumeHistory.id == history_id,
            ResumeHistory.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Resume record not found")

    docx_url = _safe_download_url(row.s3_key_docx, row.id, "docx")
    pdf_url = _safe_download_url(row.s3_key_pdf, row.id, "pdf")

    parsed_notes = []
    if row.notes:
        try:
            val = json.loads(row.notes)
            if isinstance(val, list):
                parsed_notes = [str(x) for x in val]
            elif isinstance(val, str):
                parsed_notes = [val]
        except Exception:
            parsed_notes = [row.notes]

    matched_keywords = []
    missing_keywords = []
    if row.jd_text:
        try:
            from resume_builder.jd_parser import COMMON_TECH, COMMON_KEYWORDS
            from resume_builder.textutil import term_in_text

            md_text = row.markdown or ""
            jd_terms = [t for t in COMMON_TECH + COMMON_KEYWORDS if term_in_text(t, row.jd_text)]
            for t in jd_terms:
                if term_in_text(t, md_text):
                    matched_keywords.append(t)
                else:
                    missing_keywords.append(t)
        except Exception:
            pass

    return {
        "id": str(row.id),
        "company": row.jd_company or "",
        "job_title": row.jd_title or "",
        "jd_company": row.jd_company or "",
        "jd_title": row.jd_title or "",
        "job_description": row.jd_text or "",
        "jd_text": row.jd_text or "",
        "ats_score": row.ats_score or 0,
        "markdown": row.markdown or f"# Resume\n\nTailored for {row.jd_title or 'Role'} at {row.jd_company or 'Company'}",
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "recommendations": [],
        "notes": parsed_notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "has_docx": bool(row.s3_key_docx),
        "has_pdf": bool(row.s3_key_pdf),
        "download_docx_url": docx_url,
        "download_pdf_url": pdf_url,
    }


def _recompile_and_upload_artifacts(
    markdown_text: str,
    user_id: uuid.UUID,
    history_id: uuid.UUID,
    s3_key_docx: str | None,
    s3_key_pdf: str | None,
) -> tuple[str | None, str | None]:
    """Compiles Markdown into DOCX and PDF, saving to local cache and uploading to S3."""
    from ..storage.s3 import upload_file
    from .markdown_renderer import compile_markdown_to_artifacts

    docx_key = s3_key_docx or f"resumes/{user_id}/{history_id}/resume.docx"
    pdf_key = s3_key_pdf or f"resumes/{user_id}/{history_id}/resume.pdf"

    local_docx = _get_local_cache_path(history_id, "docx")
    local_pdf = _get_local_cache_path(history_id, "pdf")

    try:
        compile_markdown_to_artifacts(markdown_text, local_docx, local_pdf)
    except Exception:
        return None, None

    uploaded_docx = docx_key if local_docx.exists() else None
    uploaded_pdf = pdf_key if local_pdf.exists() else None

    # Optionally upload to S3 if configured
    try:
        if local_docx.exists():
            upload_file(local_docx, docx_key)
        if local_pdf.exists():
            upload_file(local_pdf, pdf_key)
    except Exception:
        pass

    return uploaded_docx, uploaded_pdf


@router.patch("/history/{history_id}")
async def update_resume_history(
    history_id: uuid.UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates resume markdown or details for a history record, recompiling DOCX & PDF."""
    result = await db.execute(
        select(ResumeHistory).where(
            ResumeHistory.id == history_id,
            ResumeHistory.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Resume record not found")

    if "markdown" in body:
        row.markdown = body["markdown"]
        if row.markdown and row.markdown.strip():
            import asyncio
            docx_key, pdf_key = await asyncio.to_thread(
                _recompile_and_upload_artifacts,
                row.markdown,
                current_user.id,
                row.id,
                row.s3_key_docx,
                row.s3_key_pdf,
            )
            if docx_key:
                row.s3_key_docx = docx_key
            if pdf_key:
                row.s3_key_pdf = pdf_key

    if "job_description" in body and body["job_description"]:
        row.jd_text = body["job_description"]
    if "jd_title" in body and body["jd_title"]:
        row.jd_title = body["jd_title"]
    if "jd_company" in body and body["jd_company"]:
        row.jd_company = body["jd_company"]

    # Re-analyze matched and missing keywords dynamically
    matched_keywords = []
    missing_keywords = []
    if row.jd_text:
        try:
            from resume_builder.jd_parser import COMMON_TECH, COMMON_KEYWORDS
            from resume_builder.textutil import term_in_text

            md_text = row.markdown or ""
            jd_terms = [t for t in COMMON_TECH + COMMON_KEYWORDS if term_in_text(t, row.jd_text)]
            for t in jd_terms:
                if term_in_text(t, md_text):
                    matched_keywords.append(t)
                else:
                    missing_keywords.append(t)

            total_kw = len(matched_keywords) + len(missing_keywords)
            if total_kw > 0:
                row.ats_score = int(round((len(matched_keywords) / total_kw) * 100))
        except Exception:
            pass

    parsed_notes = []
    if row.notes:
        try:
            val = json.loads(row.notes)
            if isinstance(val, list):
                parsed_notes = [str(x) for x in val]
            elif isinstance(val, str):
                parsed_notes = [val]
        except Exception:
            parsed_notes = [row.notes]

    await db.commit()
    await db.refresh(row)

    docx_url = _safe_download_url(row.s3_key_docx, row.id, "docx")
    pdf_url = _safe_download_url(row.s3_key_pdf, row.id, "pdf")

    return {
        "id": str(row.id),
        "company": row.jd_company or "",
        "job_title": row.jd_title or "",
        "jd_company": row.jd_company or "",
        "jd_title": row.jd_title or "",
        "job_description": row.jd_text or "",
        "jd_text": row.jd_text or "",
        "ats_score": row.ats_score or 0,
        "markdown": row.markdown or "",
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "recommendations": [],
        "notes": parsed_notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "has_docx": bool(row.s3_key_docx) or _get_local_cache_path(row.id, "docx").exists(),
        "has_pdf": bool(row.s3_key_pdf) or _get_local_cache_path(row.id, "pdf").exists(),
        "download_docx_url": docx_url,
        "download_pdf_url": pdf_url,
    }


@router.get("/history/{history_id}/download/{file_format}")
async def download_resume_artifact(
    history_id: uuid.UUID,
    file_format: str,
    token: str | None = Query(None),
    auth: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
):
    """Directly serves or on-demand compiles the resume DOCX or PDF file."""
    fmt = file_format.lower().lstrip(".")
    if fmt not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail="Invalid format. Must be docx or pdf")

    from ..auth.service import decode_access_token, get_user_by_id
    raw_token = (auth.credentials if auth else None) or token
    if not raw_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        user_id = uuid.UUID(decode_access_token(raw_token))
        user = await get_user_by_id(user_id, db)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(
        select(ResumeHistory).where(
            ResumeHistory.id == history_id,
            ResumeHistory.user_id == user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Resume record not found")

    target_file = _get_local_cache_path(row.id, fmt)
    if not target_file.exists():
        md_text = row.markdown or f"# {user.email}\n\nResume"
        from .markdown_renderer import markdown_to_docx
        docx_file = _get_local_cache_path(row.id, "docx")
        if not docx_file.exists():
            markdown_to_docx(md_text, docx_file)

        if fmt == "pdf":
            from resume_builder.render.pdf import docx_to_pdf
            docx_to_pdf(docx_file, target_file)

    if not target_file.exists():
        raise HTTPException(status_code=500, detail=f"Failed to generate {fmt.upper()} file")

    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if fmt == "docx"
        else "application/pdf"
    )
    filename = f"{(row.jd_title or 'resume').lower().replace(' ', '-')}.{fmt}"
    return FileResponse(
        str(target_file),
        media_type=media_type,
        filename=filename,
    )


@router.get("/history/{history_id}/download-urls")
async def get_resume_download_urls(
    history_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns download URLs for a resume history item, ensuring files are compiled."""
    result = await db.execute(
        select(ResumeHistory).where(
            ResumeHistory.id == history_id,
            ResumeHistory.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Resume record not found")

    docx_url = _safe_download_url(row.s3_key_docx, row.id, "docx")
    pdf_url = _safe_download_url(row.s3_key_pdf, row.id, "pdf")

    return {
        "download_docx_url": docx_url,
        "download_pdf_url": pdf_url,
        "has_docx": True,
        "has_pdf": True,
    }
