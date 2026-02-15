"""
Authentication API endpoints.

Handles user registration, login, token refresh, profile retrieval,
and cross-service user provisioning.

For Developers:
    The provision endpoint is protected by API key and creates users
    on behalf of the dropshipping platform.

For QA Engineers:
    Test: registration (success + duplicate email), login (success + wrong
    password), refresh (success + invalid token), profile, provisioning.

For End Users:
    Register at /auth/register, login at /auth/login, refresh tokens
    at /auth/refresh, and view your profile at /auth/me.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_or_api_key
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    ProvisionRequest,
    ProvisionResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_by_id,
    provision_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account.

    Creates an account with the provided email and password, and returns
    JWT tokens for immediate authentication.

    Args:
        request: Registration data (email, password).
        db: Database session.

    Returns:
        TokenResponse with access and refresh tokens.

    Raises:
        HTTPException 409: If email is already registered.
    """
    try:
        user = await register_user(db, request.email, request.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate with email and password.

    Verifies credentials and returns JWT tokens on success.

    Args:
        request: Login credentials (email, password).
        db: Database session.

    Returns:
        TokenResponse with access and refresh tokens.

    Raises:
        HTTPException 401: If credentials are invalid.
    """
    user = await authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Refresh an expired access token.

    Validates the refresh token and issues a new token pair.

    Args:
        request: Refresh token.
        db: Database session.

    Returns:
        TokenResponse with new access and refresh tokens.

    Raises:
        HTTPException 401: If refresh token is invalid or expired.
    """
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    import uuid

    user = await get_user_by_id(db, uuid.UUID(payload["sub"]))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
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
    # TODO: Implement actual email sending
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

    Requires admin-level API key authentication.

    Args:
        request: Provisioning data (email, plan, external IDs).
        current_user: The authenticated platform service account.
        db: Database session.

    Returns:
        ProvisionResponse with user ID and API key.
    """
    user, api_key = await provision_user(
        db,
        email=request.email,
        password=request.password,
        plan=request.plan,
        external_platform_id=request.external_platform_id,
        external_store_id=request.external_store_id,
    )

    return ProvisionResponse(user_id=user.id, api_key=api_key)
