"""Authentication API router.

Provides endpoints for user registration, login, token refresh,
password reset (stubbed), and retrieving the current user's profile.

**For Developers:**
    All endpoints are prefixed with ``/auth`` (the full path becomes
    ``/api/v1/auth/...`` after the router is included in ``main.py``).

**For End Users:**
    - Register with email and password to create an account.
    - Login to receive access and refresh tokens.
    - Use the access token in the ``Authorization: Bearer`` header for
      protected endpoints.
    - Refresh your access token before it expires (15 min) using the
      refresh token.

**For QA Engineers:**
    - Registration with a duplicate email returns 409.
    - Login with invalid credentials returns 401.
    - Refresh with an invalid or expired token returns 401.
    - ``GET /auth/me`` without a token returns 401.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
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
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Register a new user account and return authentication tokens.

    Args:
        request: Registration payload with email and password.
        db: Async database session injected by FastAPI.

    Returns:
        TokenResponse with access and refresh JWTs.

    Raises:
        HTTPException: 409 if a user with the given email already exists.
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
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Authenticate a user and return access/refresh tokens.

    Args:
        request: Login payload with email and password.
        db: Async database session injected by FastAPI.

    Returns:
        TokenResponse with access and refresh JWTs.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    user = await authenticate_user(db, request.email, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Exchange a valid refresh token for a new access/refresh token pair.

    Args:
        request: Payload containing the refresh token.
        db: Async database session injected by FastAPI.

    Returns:
        TokenResponse with new access and refresh JWTs.

    Raises:
        HTTPException: 401 if the refresh token is invalid, expired, or
            the associated user no longer exists.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    try:
        payload = decode_token(request.refresh_token)
        user_id_str: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id_str is None or token_type != "refresh":
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest) -> MessageResponse:
    """Initiate a password reset flow (currently stubbed).

    Always returns a success message regardless of whether the email exists,
    to prevent user enumeration.

    Args:
        request: Payload containing the email address.

    Returns:
        A message confirming the reset email was sent.
    """
    # Stubbed: in production, this would queue a Celery task to send a reset email.
    return MessageResponse(message="If an account with that email exists, a reset link has been sent.")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the profile of the currently authenticated user.

    Args:
        current_user: The authenticated user, injected by the ``get_current_user`` dependency.

    Returns:
        UserResponse with the user's id, email, status, and creation date.
    """
    return UserResponse.model_validate(current_user)
