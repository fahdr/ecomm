"""
Authentication service for the Super Admin Dashboard.

Provides JWT token creation and verification, and bcrypt password hashing.
This service is used by the auth router and the ``get_current_admin``
dependency to secure all admin endpoints.

For Developers:
    - ``hash_password(plain)`` returns a bcrypt hash.
    - ``verify_password(plain, hashed)`` checks a password against its hash.
    - ``create_access_token(data)`` encodes a JWT with an expiration claim.
    - ``decode_access_token(token)`` decodes and validates a JWT.

    The JWT payload contains ``sub`` (admin user ID as string) and ``exp``
    (expiration timestamp). The signing key is ``settings.admin_secret_key``.

For QA Engineers:
    Tokens expire after ``settings.admin_token_expire_minutes`` (default 480).
    Expired tokens must return a 401 response.
    Invalid tokens (wrong signature, malformed) must also return 401.

For Project Managers:
    Admin authentication is separate from the platform's customer auth
    and the LLM Gateway's service-key auth. This ensures admin access
    is independently controllable.

For End Users:
    This service secures the admin panel. End users authenticate
    through the separate platform customer auth system.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

# JWT algorithm constant
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt hash as a UTF-8 string.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    Args:
        password: The plaintext password to check.
        hashed: The bcrypt hash to compare against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    """
    Create a signed JWT access token.

    The token includes the provided data plus an ``exp`` claim set to
    ``settings.admin_token_expire_minutes`` from now.

    Args:
        data: Payload dict to encode. Must include ``sub`` (subject).

    Returns:
        The encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.admin_token_expire_minutes
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.admin_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Args:
        token: The encoded JWT string.

    Returns:
        The decoded payload dict containing ``sub`` and ``exp``.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is malformed or has a bad signature.
    """
    return jwt.decode(token, settings.admin_secret_key, algorithms=[ALGORITHM])
