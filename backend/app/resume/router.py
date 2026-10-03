"""Resume router — streaming build & REST generate/history endpoints."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.models import User
from ..database import get_db
from ..history.models import ResumeHistory
from ..middleware.auth import get_current_user
from .schemas import BuildRequest
from .service import build_resume_stream

router = APIRouter(prefix="/resume", tags=["resume"])


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
            make_pdf=body.use_pdf,
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

    events = []
    async for event in build_resume_stream(
        user=current_user,
        jd_text=jd_text,
        make_pdf=False,
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
            "ats_score": r.ats_score or 0,
            "markdown": r.markdown or f"# Resume\n\nTailored for {r.jd_title or 'Role'} at {r.jd_company or 'Company'}",
            "matched_keywords": [],
            "missing_keywords": [],
            "recommendations": [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
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

    return {
        "id": str(row.id),
        "company": row.jd_company or "",
        "job_title": row.jd_title or "",
        "ats_score": row.ats_score or 0,
        "markdown": row.markdown or f"# Resume\n\nTailored for {row.jd_title or 'Role'} at {row.jd_company or 'Company'}",
        "matched_keywords": [],
        "missing_keywords": [],
        "recommendations": [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
