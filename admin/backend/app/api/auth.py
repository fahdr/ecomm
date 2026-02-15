"""
Admin authentication router for the Super Admin Dashboard.

Provides login, profile, and initial setup endpoints. The setup endpoint
is a one-time operation that creates the first super_admin user when no
admin accounts exist in the database.

For Developers:
    - ``POST /auth/login``: Authenticates with email + password, returns JWT.
    - ``GET /auth/me``: Returns the currently authenticated admin's profile.
    - ``POST /auth/setup``: Creates the first admin user (only when DB is empty).

    Login uses bcrypt verification via ``auth_service.verify_password``.
    Tokens are signed with ``settings.admin_secret_key`` (separate from
    the platform JWT and the LLM Gateway service key).

For QA Engineers:
    - Setup must only work once (first admin). Subsequent calls return 409.
    - Login with wrong credentials must return 401.
    - ``/auth/me`` without a token must return 401/403.
    - ``/auth/me`` with a valid token must return the admin's email and role.

For Project Managers:
    The setup flow is designed for first-time deployment. After the first
    super_admin is created, additional admins are created through the
    dashboard (future endpoint).

For End Users:
    Admin authentication is separate from customer authentication.
    This system is used exclusively by platform operators.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.database import get_db
from app.models.admin_user import AdminUser
from app.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter()


# --------------------------------------------------------------------------- #
#  Request / Response schemas
# --------------------------------------------------------------------------- #


class LoginRequest(BaseModel):
    """
    Schema for the admin login request.

    Attributes:
        email: The admin's registered email address.
        password: The admin's plaintext password.
    """

    email: str
    password: str


class SetupRequest(BaseModel):
    """
    Schema for the initial admin setup request.

    Attributes:
        email: The email address for the first super_admin.
        password: The password for the first super_admin (min 8 chars recommended).
    """

    email: str
    password: str


class TokenResponse(BaseModel):
    """
    Schema for the JWT token response.

    Attributes:
        access_token: The signed JWT access token.
        token_type: The token type (always ``bearer``).
    """

    access_token: str
    token_type: str = "bearer"


class AdminUserResponse(BaseModel):
    """
    Schema for the admin user profile response.

    Attributes:
        id: The admin user's UUID.
        email: The admin's email address.
        role: The admin's access level (super_admin, admin, viewer).
        is_active: Whether the account is enabled.
    """

    id: str
    email: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------- #
#  Endpoints
# --------------------------------------------------------------------------- #


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate an admin user and return a JWT.

    Verifies the email/password combination against the database.
    Returns a signed JWT containing the admin's ID as the subject.

    Args:
        body: Login credentials (email and password).
        db: The async database session.

    Returns:
        TokenResponse with the signed JWT access token.

    Raises:
        HTTPException(401): If the email is not found or password is wrong.
    """
    result = await db.execute(
        select(AdminUser).where(AdminUser.email == body.email)
    )
    admin = result.scalar_one_or_none()

    if admin is None or not verify_password(body.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is deactivated",
        )

    token = create_access_token({"sub": str(admin.id)})
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=AdminUserResponse)
async def get_me(current_admin: AdminUser = Depends(get_current_admin)):
    """
    Return the currently authenticated admin's profile.

    Args:
        current_admin: The authenticated admin user (injected by dependency).

    Returns:
        AdminUserResponse with the admin's ID, email, role, and active status.
    """
    return AdminUserResponse(
        id=str(current_admin.id),
        email=current_admin.email,
        role=current_admin.role,
        is_active=current_admin.is_active,
    )


@router.post("/auth/setup", response_model=AdminUserResponse, status_code=201)
async def setup_first_admin(
    body: SetupRequest, db: AsyncSession = Depends(get_db)
):
    """
    Create the first super_admin account (one-time setup).

    This endpoint only works when no admin users exist in the database.
    It creates a super_admin account with the provided email and password.
    Subsequent calls return 409 Conflict.

    Args:
        body: Setup credentials (email and password).
        db: The async database session.

    Returns:
        AdminUserResponse for the newly created super_admin.

    Raises:
        HTTPException(409): If any admin user already exists.
    """
    result = await db.execute(select(func.count(AdminUser.id)))
    count = result.scalar()

    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin user already exists. Use login instead.",
        )

    admin = AdminUser(
        email=body.email,
        hashed_password=hash_password(body.password),
        role="super_admin",
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)

    return AdminUserResponse(
        id=str(admin.id),
        email=admin.email,
        role=admin.role,
        is_active=admin.is_active,
    )
