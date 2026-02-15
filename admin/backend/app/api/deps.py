"""
FastAPI dependencies for the Super Admin Dashboard.

Provides the ``get_current_admin`` dependency that extracts and validates
the JWT token from the Authorization header, then loads the corresponding
AdminUser from the database.

For Developers:
    Use ``Depends(get_current_admin)`` on any endpoint that requires
    admin authentication. The dependency returns the ``AdminUser`` ORM
    object, so you can access ``current_admin.role``, ``.email``, etc.

    The Authorization header must contain ``Bearer <token>``. Tokens are
    signed with ``settings.admin_secret_key`` using HS256.

For QA Engineers:
    Test that missing, expired, and invalid tokens return 401.
    Test that a deactivated admin (``is_active=False``) returns 401.
    Test that a valid token returns the correct admin user.

For Project Managers:
    This dependency enforces that all admin endpoints (except setup and
    login) require a valid admin session. It is the first line of defense
    for the admin panel.

For End Users:
    This ensures only authorized platform administrators can access
    the admin dashboard's management features.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.services.auth_service import decode_access_token

# HTTP Bearer scheme for extracting JWT from Authorization header
security = HTTPBearer()


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """
    FastAPI dependency that validates the JWT and returns the admin user.

    Extracts the Bearer token from the Authorization header, decodes it,
    looks up the admin user by ID, and verifies the account is active.

    Args:
        credentials: The HTTP Bearer token extracted by FastAPI.
        db: The async database session.

    Returns:
        The authenticated AdminUser ORM object.

    Raises:
        HTTPException(401): If the token is missing, invalid, expired,
            or the admin user does not exist or is deactivated.
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        admin_id = payload.get("sub")
        if admin_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    import uuid as uuid_mod

    admin = await db.get(AdminUser, uuid_mod.UUID(admin_id))
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin user not found",
        )
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is deactivated",
        )
    return admin
