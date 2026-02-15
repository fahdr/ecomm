"""
Authentication request and response schemas.

Defines the data structures for user registration, login, token refresh,
and profile endpoints.

For Developers:
    All schemas use Pydantic v2 with strict validation. EmailStr validates
    email format. Password requires minimum 8 characters.

For QA Engineers:
    Test validation: invalid emails should return 422, short passwords
    should be rejected, and token responses should contain both tokens.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from ecomm_core.models.user import PlanTier


class RegisterRequest(BaseModel):
    """
    User registration request.

    Attributes:
        email: Valid email address for the new account.
        password: Password (minimum 8 characters).
    """

    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")


class LoginRequest(BaseModel):
    """
    User login request.

    Attributes:
        email: Email address of the account.
        password: Account password.
    """

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """
    JWT token pair response returned after successful auth.

    Attributes:
        access_token: Short-lived JWT for API access.
        refresh_token: Long-lived JWT for obtaining new access tokens.
        token_type: Always 'bearer'.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """
    Token refresh request.

    Attributes:
        refresh_token: Valid refresh token to exchange for new tokens.
    """

    refresh_token: str


class UserResponse(BaseModel):
    """
    User profile response.

    Attributes:
        id: User's unique identifier.
        email: User's email address.
        is_active: Whether the account is active.
        plan: Current subscription tier.
        created_at: Account creation timestamp.
    """

    id: uuid.UUID
    email: str
    is_active: bool
    plan: PlanTier
    created_at: datetime

    model_config = {"from_attributes": True}


class ProvisionRequest(BaseModel):
    """
    User provisioning request from the dropshipping platform.

    Attributes:
        email: Email for the new account.
        password: Optional password (generated if not provided).
        plan: Plan tier to assign.
        external_platform_id: User ID in the dropshipping platform.
        external_store_id: Store ID in the dropshipping platform (optional).
    """

    email: EmailStr
    password: str | None = None
    plan: PlanTier = PlanTier.free
    external_platform_id: str
    external_store_id: str | None = None


class ProvisionResponse(BaseModel):
    """
    Response after successful user provisioning.

    Attributes:
        user_id: ID of the created/existing user in this service.
        api_key: API key for the platform to use (shown only once).
    """

    user_id: uuid.UUID
    api_key: str


class MessageResponse(BaseModel):
    """
    Simple message response.

    Attributes:
        message: Human-readable status message.
    """

    message: str
