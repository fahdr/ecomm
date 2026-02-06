"""Authentication business logic.

Handles password hashing, JWT creation/validation, user registration, and
credential verification. This module is consumed by the auth router and the
``get_current_user`` dependency.

**For Developers:**
    - Passwords are hashed with bcrypt directly (``bcrypt`` library).
    - JWTs are signed with HS256 via ``python-jose``.
    - All database operations are async and expect an ``AsyncSession``.

**For QA Engineers:**
    - Access tokens expire after ``jwt_access_token_expire_minutes`` (default 15 min).
    - Refresh tokens expire after ``jwt_refresh_token_expire_days`` (default 7 days).
    - Duplicate email registration raises ``ValueError``.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        password: The plain-text password to hash.

    Returns:
        The bcrypt hash string.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash.

    Args:
        plain_password: The plain-text password to check.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: uuid.UUID) -> str:
    """Create a short-lived JWT access token.

    Args:
        user_id: The user's UUID to embed in the token payload.

    Returns:
        An encoded JWT string with ``sub``, ``exp``, and ``type`` claims.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Create a long-lived JWT refresh token.

    Args:
        user_id: The user's UUID to embed in the token payload.

    Returns:
        An encoded JWT string with ``sub``, ``exp``, and ``type`` claims.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Args:
        token: The encoded JWT string.

    Returns:
        The decoded payload dictionary containing ``sub``, ``exp``, and ``type``.

    Raises:
        JWTError: If the token is expired, tampered with, or otherwise invalid.
    """
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    """Register a new user account.

    Args:
        db: Async database session.
        email: The user's email address (must be unique).
        password: Plain-text password to hash and store.

    Returns:
        The newly created User ORM instance.

    Raises:
        ValueError: If a user with the given email already exists.
    """
    # Check for existing user with the same email.
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none() is not None:
        raise ValueError("A user with this email already exists")

    user = User(
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Authenticate a user by email and password.

    Args:
        db: Async database session.
        email: The email address to look up.
        password: The plain-text password to verify.

    Returns:
        The User instance if credentials are valid, or None if authentication fails.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Retrieve a user by their UUID.

    Args:
        db: Async database session.
        user_id: The UUID of the user to retrieve.

    Returns:
        The User instance if found, or None if no user exists with that ID.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
