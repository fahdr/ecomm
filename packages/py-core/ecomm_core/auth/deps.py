"""
FastAPI dependency injection factories for authentication.

Provides factory functions that create auth dependencies bound to a
specific settings instance, avoiding global state.

For Developers:
    Use the factory functions to create dependencies for your service:
        get_current_user = create_get_current_user(settings)
        get_current_user_or_api_key = create_get_current_user_or_api_key(settings)

For QA Engineers:
    Test unauthenticated access (should return 401), expired tokens,
    invalid API keys, and plan limit enforcement (should return 403).
"""

import uuid
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.auth.service import decode_token, get_user_by_api_key, get_user_by_id
from ecomm_core.models.user import User

# Support both Bearer token and optional header
bearer_scheme = HTTPBearer(auto_error=False)


def create_get_current_user(get_db: Callable) -> Callable:
    """
    Factory that creates a get_current_user dependency bound to settings.

    The returned dependency uses the service's get_db and settings for
    JWT decoding.

    Args:
        get_db: The service's get_db dependency function.

    Returns:
        A FastAPI dependency function for JWT authentication.
    """

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
            HTTPException: 401 if token is missing, invalid, or user not found.
        """
        # Import settings lazily from the calling service
        from app.config import settings

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = decode_token(
            credentials.credentials,
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
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

    return get_current_user


def create_get_current_user_or_api_key(get_db: Callable) -> Callable:
    """
    Factory that creates a dual-auth dependency (JWT or API key).

    Args:
        get_db: The service's get_db dependency function.

    Returns:
        A FastAPI dependency function for JWT or API key authentication.
    """

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
        from app.config import settings

        # Try JWT first
        if credentials:
            payload = decode_token(
                credentials.credentials,
                secret_key=settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
            )
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

    return get_current_user_or_api_key
