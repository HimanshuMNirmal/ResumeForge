"""AES-256-GCM encryption for API keys + key CRUD service."""
from __future__ import annotations

import base64
import os
import uuid
from typing import Literal

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from .models import ApiKey

Provider = Literal["anthropic", "openai", "gemini"]

# Default models per provider (fast, strong)
DEFAULT_MODELS: dict[str, tuple[str, str]] = {
    "anthropic": ("claude-haiku-4-5-20251001", "claude-sonnet-5-5"),
    "openai": ("gpt-4.1-mini", "gpt-4.1"),
    "gemini": ("gemini-2.5-flash", "gemini-2.5-pro"),
}

AVAILABLE_MODELS: dict[str, dict[str, list[str]]] = {
    "anthropic": {
        "fast": ["claude-haiku-4-5-20251001", "claude-haiku-3-5-20251022"],
        "strong": ["claude-sonnet-5-5", "claude-opus-4-5", "claude-sonnet-4-5-20251022"],
    },
    "openai": {
        "fast": ["gpt-4.1-mini", "gpt-4o-mini", "gpt-3.5-turbo"],
        "strong": ["gpt-4.1", "gpt-4o", "gpt-4-turbo"],
    },
    "gemini": {
        "fast": ["gemini-2.5-flash", "gemini-1.5-flash"],
        "strong": ["gemini-2.5-pro", "gemini-1.5-pro"],
    },
}


# ── Encryption ────────────────────────────────────────────────────────────────

def _encrypt(plaintext: str) -> str:
    """AES-256-GCM encrypt, returns base64(nonce + ciphertext)."""
    key = get_settings().encryption_key_bytes
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.urlsafe_b64encode(nonce + ct).decode()


def _decrypt(token: str) -> str:
    try:
        key = get_settings().encryption_key_bytes
        aesgcm = AESGCM(key)
        raw = base64.urlsafe_b64decode(token)
        nonce, ct = raw[:12], raw[12:]
        return aesgcm.decrypt(nonce, ct, None).decode()
    except Exception as exc:
        raise ValueError(f"Failed to decrypt key: {exc}") from exc


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def list_keys(user_id: uuid.UUID, db: AsyncSession) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at)
    )
    return list(result.scalars().all())


async def add_key(
    user_id: uuid.UUID,
    label: str,
    provider: Provider,
    raw_key: str,
    model_fast: str | None,
    model_strong: str | None,
    db: AsyncSession,
) -> ApiKey:
    encrypted = _encrypt(raw_key)
    preview = raw_key[-4:] if len(raw_key) >= 4 else raw_key
    key = ApiKey(
        user_id=user_id,
        label=label,
        provider=provider,
        encrypted_key=encrypted,
        key_preview=preview,
        model_fast=model_fast,
        model_strong=model_strong,
        is_active=False,
    )
    db.add(key)
    await db.flush()
    return key


async def activate_key(key_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> ApiKey:
    """Deactivate all user keys then activate the requested one."""
    # Deactivate all
    await db.execute(
        update(ApiKey).where(ApiKey.user_id == user_id).values(is_active=False)
    )
    # Activate target
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    if key is None:
        raise ValueError("Key not found")
    key.is_active = True
    await db.flush()
    return key


async def toggle_key(key_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> ApiKey:
    """Toggle a key active/inactive. If toggling on, deactivate any other active key."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    if key is None:
        raise ValueError("Key not found")

    if key.is_active:
        key.is_active = False
    else:
        await db.execute(
            update(ApiKey).where(ApiKey.user_id == user_id).values(is_active=False)
        )
        key.is_active = True
    await db.flush()
    return key


async def delete_key(key_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    if key is None:
        raise ValueError("Key not found")
    await db.delete(key)
    await db.flush()


async def get_active_key(user_id: uuid.UUID, db: AsyncSession) -> ApiKey | None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def get_key_by_id(key_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> ApiKey | None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    return result.scalar_one_or_none()


def decrypt_key(api_key: ApiKey) -> str:
    return _decrypt(api_key.encrypted_key)
