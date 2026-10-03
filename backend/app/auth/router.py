"""Auth router: /api/v1/auth/* endpoints."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from .schemas import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse, UserOut
from .service import (
    create_access_token,
    create_refresh_token,
    create_user,
    decode_access_token,
    get_user_by_email,
    get_user_by_id,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
        path="/api/v1/auth",
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(body.email, db)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = await create_user(body.name, body.email, body.password, db)
    access_token = create_access_token(user.id)
    refresh_raw = await create_refresh_token(user.id, db)
    _set_refresh_cookie(response, refresh_raw)

    return RegisterResponse(user=UserOut.model_validate(user), access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(body.email, db)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    access_token = create_access_token(user.id)
    refresh_raw = await create_refresh_token(user.id, db)
    _set_refresh_cookie(response, refresh_raw)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        user, new_raw = await rotate_refresh_token(refresh_token, db)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    access_token = create_access_token(user.id)
    _set_refresh_cookie(response, new_raw)
    return TokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        await revoke_refresh_token(refresh_token, db)
    response.delete_cookie(_REFRESH_COOKIE, path="/api/v1/auth")


@router.get("/me", response_model=UserOut)
async def me(
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),
):
    """Used by the frontend on initial load to validate session."""
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Validate the refresh token is still good without rotating it
    import hashlib
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    from datetime import timezone
    from datetime import datetime
    from sqlalchemy import select
    from .models import RefreshToken
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked.is_(False),
        )
    )
    rt = result.scalar_one_or_none()
    if not rt or rt.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user = await get_user_by_id(rt.user_id, db)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return UserOut.model_validate(user)
