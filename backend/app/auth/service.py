"""Auth business logic: hashing, JWT, refresh token management."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from .models import RefreshToken, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Passwords ─────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Access tokens (short-lived JWT) ───────────────────────────────────────────

def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str:
    """Return user_id string or raise JWTError."""
    settings = get_settings()
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    sub: str = payload.get("sub", "")
    if not sub:
        raise JWTError("Missing subject")
    return sub


# ── Refresh tokens (opaque, stored hashed) ────────────────────────────────────

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_refresh_token(user_id: uuid.UUID, db: AsyncSession) -> str:
    settings = get_settings()
    raw = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    rt = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=expires,
    )
    db.add(rt)
    await db.flush()
    return raw


async def rotate_refresh_token(raw: str, db: AsyncSession) -> tuple[User, str]:
    """Validate old refresh token, revoke it, issue new one. Returns (user, new_raw_token)."""
    token_hash = _hash_token(raw)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked.is_(False),
        )
    )
    rt = result.scalar_one_or_none()
    if rt is None or rt.expires_at < datetime.now(timezone.utc):
        raise ValueError("Refresh token invalid or expired")

    # Revoke old token
    rt.revoked = True
    await db.flush()

    user_result = await db.execute(select(User).where(User.id == rt.user_id, User.is_active.is_(True)))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found or inactive")

    new_raw = await create_refresh_token(user.id, db)
    return user, new_raw


async def revoke_refresh_token(raw: str, db: AsyncSession) -> None:
    token_hash = _hash_token(raw)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True


# ── User CRUD ─────────────────────────────────────────────────────────────────

async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(user_id: uuid.UUID, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    return result.scalar_one_or_none()


async def create_user(name: str, email: str, password: str, db: AsyncSession) -> User:
    user = User(
        name=name,
        email=email.lower(),
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.flush()
    return user
