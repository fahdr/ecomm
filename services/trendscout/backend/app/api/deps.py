"""
FastAPI dependency injection for authentication and authorization.

Provides reusable dependencies for extracting the current user from
JWT tokens or API keys, and enforcing plan-based resource limits.

For Developers:
    Use `get_current_user` to protect endpoints requiring authentication.
    Use `get_current_user_or_api_key` for endpoints accepting both methods.
    Use `check_plan_limit` factory to enforce tier-specific limits.

For QA Engineers:
    Test unauthenticated access (should return 401), expired tokens,
    invalid API keys, and plan limit enforcement (should return 403).

For End Users:
    Authenticate with a Bearer JWT token or X-API-Key header.
"""

import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_token, get_user_by_api_key, get_user_by_id

# Support both Bearer token and optional header
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate the current user from a JWT Bearer token.

    Args:
        credentials: Bearer token from Authorization header.
        db: Async database session.

    Returns:
        The authenticated User.

    Raises:
        HTTPException: 401 if token is missing, invalid, expired, or user not found.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await get_user_by_id(db, uuid.UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_current_user_or_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Authenticate via JWT Bearer token OR X-API-Key header.

    Tries JWT first, then falls back to API key authentication.

    Args:
        request: FastAPI request object (for X-API-Key header).
        credentials: Bearer token from Authorization header.
        db: Async database session.

    Returns:
        The authenticated User.

    Raises:
        HTTPException: 401 if neither authentication method succeeds.
    """
    # Try JWT first
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub")
            if user_id:
                user = await get_user_by_id(db, uuid.UUID(user_id))
                if user:
                    return user

    # Try API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        user = await get_user_by_api_key(db, api_key)
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Provide a Bearer token or X-API-Key.",
    )
