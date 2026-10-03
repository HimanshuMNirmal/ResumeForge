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


def _to_item_out(row: ResumeHistory) -> HistoryItemOut:
    docx_url = generate_presigned_url(row.s3_key_docx) if row.s3_key_docx else None
    pdf_url = generate_presigned_url(row.s3_key_pdf) if row.s3_key_pdf else None
    return HistoryItemOut(
        id=row.id,
        jd_title=row.jd_title,
        jd_company=row.jd_company,
        ats_score=row.ats_score,
        model_used=row.model_used,
        provider_used=row.provider_used,
        has_docx=bool(row.s3_key_docx),
        has_pdf=bool(row.s3_key_pdf),
        download_docx_url=docx_url,
        download_pdf_url=pdf_url,
        created_at=row.created_at,
    )


@router.get("", response_model=HistoryListOut)
async def list_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(
        select(func.count()).where(ResumeHistory.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(ResumeHistory)
        .where(ResumeHistory.user_id == current_user.id)
        .order_by(ResumeHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
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

    # Remove S3 objects
    keys_to_delete = [k for k in [row.s3_key_docx, row.s3_key_pdf] if k]
    if keys_to_delete:
        delete_objects(keys_to_delete)

    await db.delete(row)
