"""Resume router — SSE streaming build endpoint."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.auth import get_current_user
from ..auth.models import User
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
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
            "Connection": "keep-alive",
        },
    )
