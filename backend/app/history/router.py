"""History router: /api/v1/history endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.auth import get_current_user
from ..auth.models import User
from ..storage.s3 import delete_objects, generate_presigned_url
from .models import ResumeHistory
from .schemas import HistoryDetailOut, HistoryItemOut, HistoryListOut

router = APIRouter(prefix="/history", tags=["history"])


def _safe_presigned_url(s3_key: str | None) -> str | None:
    if not s3_key:
        return None
    try:
        return generate_presigned_url(s3_key)
    except Exception:
        return None


def _safe_download_url(s3_key: str | None, history_id: uuid.UUID, fmt: str) -> str:
    if s3_key:
        try:
            url = generate_presigned_url(s3_key)
            if url:
                return url
        except Exception:
            pass
    return f"/api/v1/resume/history/{history_id}/download/{fmt}"


def _to_item_out(row: ResumeHistory) -> HistoryItemOut:
    return HistoryItemOut(
        id=row.id,
        jd_title=row.jd_title,
        jd_company=row.jd_company,
        ats_score=row.ats_score,
        model_used=row.model_used,
        provider_used=row.provider_used,
        has_docx=True,
        has_pdf=True,
        download_docx_url=f"/api/v1/resume/history/{row.id}/download/docx",
        download_pdf_url=f"/api/v1/resume/history/{row.id}/download/pdf",
        created_at=row.created_at,
    )


@router.get("", response_model=HistoryListOut)
async def list_history(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: Optional[str] = Query(default=None),
    sort_by: str = Query(default="newest"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(ResumeHistory).where(ResumeHistory.user_id == current_user.id)
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.where(
            (ResumeHistory.jd_title.ilike(term)) | (ResumeHistory.jd_company.ilike(term))
        )

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    if sort_by == "oldest":
        query = query.order_by(ResumeHistory.created_at.asc())
    elif sort_by == "score_desc":
        query = query.order_by(ResumeHistory.ats_score.desc().nullslast(), ResumeHistory.created_at.desc())
    elif sort_by == "score_asc":
        query = query.order_by(ResumeHistory.ats_score.asc().nullslast(), ResumeHistory.created_at.desc())
    else:
        query = query.order_by(ResumeHistory.created_at.desc())

    result = await db.execute(query.limit(limit).offset(offset))
    rows = result.scalars().all()
    return HistoryListOut(
        items=[_to_item_out(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{history_id}", response_model=HistoryDetailOut)
async def get_history_item(
    history_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResumeHistory).where(
            ResumeHistory.id == history_id,
            ResumeHistory.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="History entry not found")

    item = _to_item_out(row)
    return HistoryDetailOut(**item.model_dump(), jd_text=row.jd_text, notes=row.notes)


@router.get("/{history_id}/download-urls")
async def get_download_urls(
    history_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns fresh download URLs for a history item (downloads compiled on-demand)."""
    result = await db.execute(
        select(ResumeHistory).where(
            ResumeHistory.id == history_id,
            ResumeHistory.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="History entry not found")

    docx_url = _safe_download_url(row.s3_key_docx, row.id, "docx")
    pdf_url = _safe_download_url(row.s3_key_pdf, row.id, "pdf")

    return {
        "download_docx_url": docx_url,
        "download_pdf_url": pdf_url,
        "has_docx": True,
        "has_pdf": True,
    }


@router.delete("/{history_id}", status_code=204)
async def delete_history_item(
    history_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResumeHistory).where(
            ResumeHistory.id == history_id,
            ResumeHistory.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="History entry not found")

    # Remove S3 objects if present
    keys_to_delete = [k for k in [row.s3_key_docx, row.s3_key_pdf] if k]
    if keys_to_delete:
        try:
            delete_objects(keys_to_delete)
        except Exception:
            pass

    # Clean local cache if present
    import shutil
    from pathlib import Path
    cache_dir = Path("/tmp/resumeforge_cache") / str(row.id)
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)

    await db.delete(row)
    await db.commit()
