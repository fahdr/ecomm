"""Pydantic schemas for authentication endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/auth/*`` routes.

**For Developers:**
    All schemas use Pydantic v2 ``model_config`` for ORM compatibility
    where needed. Password validation is enforced at the schema level.

**For QA Engineers:**
    - ``RegisterRequest.password`` requires a minimum of 8 characters.
    - ``TokenResponse`` always returns ``token_type: "bearer"``.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Schema for user registration.

    Attributes:
        email: Valid email address for the new account.
        password: Plain-text password, minimum 8 characters.
    """

    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class LoginRequest(BaseModel):
    """Schema for user login.

    Attributes:
        email: Email address of the existing account.
        password: Plain-text password to verify.
    """

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Schema for token refresh.

    Attributes:
        refresh_token: A valid refresh JWT to exchange for a new access token.
    """

    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Schema for the forgot-password flow.

    Attributes:
        email: Email address to send the password reset link to.
    """

    email: EmailStr


class TokenResponse(BaseModel):
    """Schema returned after successful authentication.

    Attributes:
        access_token: Short-lived JWT for API authorization (15 min).
        refresh_token: Long-lived JWT for obtaining new access tokens (7 days).
        token_type: Always ``"bearer"``.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Schema for returning user profile information.

    Attributes:
        id: The user's unique identifier.
        email: The user's email address.
        is_active: Whether the account is enabled.
        created_at: When the account was created.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    is_active: bool
    created_at: datetime


class MessageResponse(BaseModel):
    """Generic message response for endpoints that don't return data.

    Attributes:
        message: Human-readable status message.
    """

    message: str
