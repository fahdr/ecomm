"""
Authentication API router factory.

Creates a FastAPI router with standard auth endpoints: register, login,
refresh, profile, forgot-password, and provision.

For Developers:
    Use `create_auth_router(get_db, get_current_user, get_current_user_or_api_key)`
    to create a router bound to your service's dependencies.

For QA Engineers:
    Test: registration (success + duplicate), login (success + wrong password),
    refresh (success + invalid token), profile, provisioning.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.auth.service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_by_id,
    provision_user,
    register_user,
)
from ecomm_core.models.user import User
from ecomm_core.schemas.auth import (
    LoginRequest,
    MessageResponse,
    ProvisionRequest,
    ProvisionResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


def create_auth_router(get_db, get_current_user, get_current_user_or_api_key) -> APIRouter:
    """
    Factory to create the auth router bound to service dependencies.

    Args:
        get_db: FastAPI dependency for database session.
        get_current_user: FastAPI dependency for JWT auth.
        get_current_user_or_api_key: FastAPI dependency for dual auth.

    Returns:
        Configured APIRouter with all auth endpoints.
    """
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/register", response_model=TokenResponse, status_code=201)
    async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
        """
        Register a new user account.

        Creates an account and returns JWT tokens for immediate authentication.

        Args:
            request: Registration data (email, password).
            db: Database session.

        Returns:
            TokenResponse with access and refresh tokens.

        Raises:
            HTTPException 409: If email is already registered.
        """
        from app.config import settings

        try:
            user = await register_user(db, request.email, request.password)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )

        return TokenResponse(
            access_token=create_access_token(
                user.id,
                secret_key=settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
                expire_minutes=settings.jwt_access_token_expire_minutes,
            ),
            refresh_token=create_refresh_token(
                user.id,
                secret_key=settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
                expire_days=settings.jwt_refresh_token_expire_days,
            ),
        )

    @router.post("/login", response_model=TokenResponse)
    async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
        """
        Authenticate with email and password.

        Args:
            request: Login credentials (email, password).
            db: Database session.

        Returns:
            TokenResponse with access and refresh tokens.

        Raises:
            HTTPException 401: If credentials are invalid.
        """
        from app.config import settings

        user = await authenticate_user(db, request.email, request.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        return TokenResponse(
            access_token=create_access_token(
                user.id,
                secret_key=settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
                expire_minutes=settings.jwt_access_token_expire_minutes,
            ),
            refresh_token=create_refresh_token(
                user.id,
                secret_key=settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
                expire_days=settings.jwt_refresh_token_expire_days,
            ),
        )

    @router.post("/refresh", response_model=TokenResponse)
    async def refresh(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
        """
        Refresh an expired access token.

        Args:
            request: Refresh token.
            db: Database session.

        Returns:
            TokenResponse with new access and refresh tokens.

        Raises:
            HTTPException 401: If refresh token is invalid or expired.
        """
        from app.config import settings

        payload = decode_token(
            request.refresh_token,
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user = await get_user_by_id(db, uuid.UUID(payload["sub"]))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        return TokenResponse(
            access_token=create_access_token(
                user.id,
                secret_key=settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
                expire_minutes=settings.jwt_access_token_expire_minutes,
            ),
            refresh_token=create_refresh_token(
                user.id,
                secret_key=settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
                expire_days=settings.jwt_refresh_token_expire_days,
            ),
        )

    @router.get("/me", response_model=UserResponse)
    async def get_profile(current_user: User = Depends(get_current_user)):
        """
        Get the authenticated user's profile.

        Args:
            current_user: The authenticated user (injected via dependency).

        Returns:
            UserResponse with profile information.
        """
        return current_user

    @router.post("/forgot-password", response_model=MessageResponse)
    async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):
        """
        Request a password reset email.

        Always returns success to prevent email enumeration.

        Args:
            email: The email address to send reset instructions to.
            db: Database session.

        Returns:
            MessageResponse confirming the request.
        """
        return MessageResponse(message="If an account exists, a reset email has been sent.")

    @router.post("/provision", response_model=ProvisionResponse, status_code=201)
    async def provision(
        request: ProvisionRequest,
        current_user: User = Depends(get_current_user_or_api_key),
        db: AsyncSession = Depends(get_db),
    ):
        """
        Provision a user from the dropshipping platform.

        Creates a new user account (or links an existing one) and generates
        an API key for the platform to use for subsequent requests.

        Args:
            request: Provisioning data (email, plan, external IDs).
            current_user: The authenticated platform service account.
            db: Database session.

        Returns:
            ProvisionResponse with user ID and API key.
        """
        from app.config import settings

        user, api_key = await provision_user(
            db,
            email=request.email,
            password=request.password,
            plan=request.plan,
            external_platform_id=request.external_platform_id,
            external_store_id=request.external_store_id,
            service_name=settings.service_name,
        )

        return ProvisionResponse(user_id=user.id, api_key=api_key)

    return router
