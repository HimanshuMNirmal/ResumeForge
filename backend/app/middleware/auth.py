"""JWT Bearer dependency — extracts and validates the access token."""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

_bearer = HTTPBearer(auto_error=True)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> uuid.UUID:
    """Return the authenticated user's UUID from the Bearer token."""
    from ..auth.service import decode_access_token  # local import to avoid circular
    try:
        user_id_str = decode_access_token(credentials.credentials)
        return uuid.UUID(user_id_str)
    except (JWTError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return the full User ORM object for the authenticated request."""
    from ..auth.service import get_user_by_id
    from ..auth.models import User
    user = await get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
