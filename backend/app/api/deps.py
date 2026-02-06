"""Shared FastAPI dependencies for API routes.

Provides reusable dependencies such as ``get_current_user`` that can be
injected into any route handler that requires an authenticated user.

**For Developers:**
    Use ``current_user: User = Depends(get_current_user)`` in route
    signatures to enforce authentication and receive the caller's User object.

**For QA Engineers:**
    Any request missing a valid ``Authorization: Bearer <token>`` header
    will receive a 401 response with ``"Could not validate credentials"``.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_token, get_user_by_id

# OAuth2 scheme extracts the Bearer token from the Authorization header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency that resolves the current authenticated user.

    Extracts the JWT from the ``Authorization: Bearer`` header, decodes it,
    and loads the corresponding user from the database.

    Args:
        token: The JWT access token, automatically extracted by OAuth2PasswordBearer.
        db: Async database session injected by FastAPI.

    Returns:
        The authenticated User ORM instance.

    Raises:
        HTTPException: 401 if the token is invalid, expired, not an access token,
            or the user does not exist / is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id_str: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id_str is None or token_type != "access":
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user
