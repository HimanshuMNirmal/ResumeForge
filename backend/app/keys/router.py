"""Keys router: /api/v1/keys endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.auth import get_current_user
from ..auth.models import User
from .schemas import AddKeyRequest, AvailableModelsOut, KeyOut
from .service import AVAILABLE_MODELS, activate_key, add_key, delete_key, get_active_key, list_keys
import uuid

router = APIRouter(prefix="/keys", tags=["keys"])


@router.get("", response_model=list[KeyOut])
async def get_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    keys = await list_keys(current_user.id, db)
    return [KeyOut.model_validate(k) for k in keys]


@router.post("", response_model=KeyOut, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: AddKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key = await add_key(
        user_id=current_user.id,
        label=body.label,
        provider=body.provider,
        raw_key=body.raw_key,
        model_fast=body.model_fast,
        model_strong=body.model_strong,
        db=db,
    )
    return KeyOut.model_validate(key)


@router.put("/{key_id}/activate", response_model=KeyOut)
async def activate(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        key = await activate_key(key_id, current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return KeyOut.model_validate(key)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_key(key_id, current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/models", response_model=AvailableModelsOut)
async def get_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return available model options for the user's active provider."""
    active = await get_active_key(current_user.id, db)
    provider = active.provider if active else "anthropic"
    models = AVAILABLE_MODELS.get(provider, {})
    return AvailableModelsOut(
        provider=provider,
        fast_models=models.get("fast", []),
        strong_models=models.get("strong", []),
    )
