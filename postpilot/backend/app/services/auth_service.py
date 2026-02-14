"""
Authentication service handling JWT tokens and password management.

Provides all auth-related operations: registration, login, token creation,
token validation, and password hashing.

For Developers:
    Uses bcrypt for password hashing and python-jose for JWT.
    Access tokens are short-lived (15min), refresh tokens long-lived (7 days).
    The `provision_user` function is used for cross-service user creation.

For QA Engineers:
    Test token expiry, refresh flow, invalid credentials, duplicate emails.
    Provisioned users should have external_platform_id set.

For End Users:
    Sign up with your email, log in to get access tokens, refresh when expired.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.api_key import ApiKey
from app.models.user import PlanTier, User


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with auto-generated salt.

    Args:
        password: Plain text password to hash.

    Returns:
        Bcrypt hash string.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a bcrypt hash.

    Args:
        plain_password: The plain text password to check.
        hashed_password: The bcrypt hash to verify against.

    Returns:
        True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(user_id: uuid.UUID) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        user_id: The user's UUID to encode in the token.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: uuid.UUID) -> str:
    """
    Create a long-lived JWT refresh token.

    Args:
        user_id: The user's UUID to encode in the token.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT string to decode.

    Returns:
        Token payload dict if valid, None if invalid or expired.
    """
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None


async def register_user(
    db: AsyncSession, email: str, password: str
) -> User:
    """
    Register a new user account.

    Args:
        db: Async database session.
        email: User's email address (must be unique).
        password: Plain text password (will be hashed).

    Returns:
        The newly created User.

    Raises:
        ValueError: If a user with this email already exists.
    """
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise ValueError("A user with this email already exists")

    user = User(
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User | None:
    """
    Authenticate a user with email and password.

    Args:
        db: Async database session.
        email: User's email address.
        password: Plain text password to verify.

    Returns:
        The authenticated User if credentials are valid, None otherwise.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """
    Get a user by their UUID.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        The User if found and active, None otherwise.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and not user.is_active:
        return None
    return user


async def provision_user(
    db: AsyncSession,
    email: str,
    password: str | None,
    plan: PlanTier,
    external_platform_id: str,
    external_store_id: str | None = None,
) -> tuple[User, str]:
    """
    Provision a user from the dropshipping platform.

    Creates a new user (or returns existing) and generates an API key
    for the platform to use for subsequent requests.

    Args:
        db: Async database session.
        email: User's email address.
        password: Optional password (random if not provided).
        plan: Plan tier to assign.
        external_platform_id: User ID in the dropshipping platform.
        external_store_id: Store ID in the dropshipping platform.

    Returns:
        Tuple of (User, api_key_string). The API key is only returned once.
    """
    # Check for existing user with this external ID
    result = await db.execute(
        select(User).where(User.external_platform_id == external_platform_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Check by email
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if not user:
        # Create new user
        actual_password = password or secrets.token_urlsafe(32)
        user = User(
            email=email,
            hashed_password=hash_password(actual_password),
            plan=plan,
            external_platform_id=external_platform_id,
            external_store_id=external_store_id,
        )
        db.add(user)
        await db.flush()
    else:
        # Update existing user's platform linkage
        user.external_platform_id = external_platform_id
        if external_store_id:
            user.external_store_id = external_store_id
        if plan != PlanTier.free:
            user.plan = plan

    # Generate API key for the platform
    raw_key = f"{settings.service_name[:2]}_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        user_id=user.id,
        name=f"Platform Integration ({external_platform_id[:8]})",
        key_hash=key_hash,
        key_prefix=raw_key[:12],
        scopes=["read", "write", "admin"],
    )
    db.add(api_key)
    await db.flush()

    return user, raw_key


async def get_user_by_api_key(db: AsyncSession, raw_key: str) -> User | None:
    """
    Authenticate a user via API key.

    Args:
        db: Async database session.
        raw_key: The raw API key string.

    Returns:
        The User if the key is valid and active, None otherwise.
    """
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        return None

    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.now(UTC):
        return None

    # Update last used
    api_key.last_used_at = datetime.now(UTC)

    # Load user
    return await get_user_by_id(db, api_key.user_id)
