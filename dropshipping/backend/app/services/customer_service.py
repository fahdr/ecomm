"""Customer account business logic.

Handles customer registration, authentication, JWT token creation,
password reset flow, and guest order linking for storefront accounts.

**For Developers:**
    Customer accounts are separate from platform User accounts. Users
    own/manage stores; customers are shoppers on the storefront. Customer
    JWTs use ``aud: "customer"`` to distinguish from store-owner tokens.

**For QA Engineers:**
    - Registration enforces unique email per store.
    - Guest orders (same email, same store) are NOT auto-linked to
      ``customer_id`` — the customer can still view them by email match.
    - Password reset tokens expire after 1 hour.
    - Customer access tokens expire after 60 minutes (longer than owner tokens).

**For End Users:**
    This service powers your storefront account — registration, login,
    and password management.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.customer import CustomerAccount


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        password: The plain-text password.

    Returns:
        The bcrypt hash string.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash.

    Args:
        plain_password: The password to check.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_customer_access_token(customer_id: uuid.UUID, store_id: uuid.UUID) -> str:
    """Create a JWT access token for a customer.

    The token includes ``aud: "customer"`` to distinguish from store-owner
    tokens and ``store_id`` to scope the token to a specific store.

    Args:
        customer_id: The customer's UUID.
        store_id: The store's UUID.

    Returns:
        An encoded JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    payload = {
        "sub": str(customer_id),
        "store_id": str(store_id),
        "aud": "customer",
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_customer_refresh_token(customer_id: uuid.UUID, store_id: uuid.UUID) -> str:
    """Create a long-lived JWT refresh token for a customer.

    Args:
        customer_id: The customer's UUID.
        store_id: The store's UUID.

    Returns:
        An encoded JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    payload = {
        "sub": str(customer_id),
        "store_id": str(store_id),
        "aud": "customer",
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_password_reset_token(customer_id: uuid.UUID) -> str:
    """Create a short-lived token for password reset.

    Args:
        customer_id: The customer's UUID.

    Returns:
        An encoded JWT string (1 hour expiry).
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {
        "sub": str(customer_id),
        "type": "password_reset",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def register_customer(
    db: AsyncSession,
    store_id: uuid.UUID,
    email: str,
    password: str,
    first_name: str | None = None,
    last_name: str | None = None,
) -> CustomerAccount:
    """Register a new customer account for a store.

    Args:
        db: Async database session.
        store_id: The store this customer belongs to.
        email: Customer email (must be unique within the store).
        password: Plain-text password to hash.
        first_name: Optional first name.
        last_name: Optional last name.

    Returns:
        The newly created CustomerAccount.

    Raises:
        ValueError: If a customer with this email already exists in the store.
    """
    result = await db.execute(
        select(CustomerAccount).where(
            CustomerAccount.store_id == store_id,
            CustomerAccount.email == email,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise ValueError("An account with this email already exists")

    customer = CustomerAccount(
        store_id=store_id,
        email=email,
        hashed_password=hash_password(password),
        first_name=first_name,
        last_name=last_name,
    )
    db.add(customer)
    await db.flush()
    return customer


async def authenticate_customer(
    db: AsyncSession,
    store_id: uuid.UUID,
    email: str,
    password: str,
) -> CustomerAccount | None:
    """Authenticate a customer by email and password within a store.

    Args:
        db: Async database session.
        store_id: The store to authenticate against.
        email: The email to look up.
        password: The plain-text password to verify.

    Returns:
        The CustomerAccount if credentials are valid, None otherwise.
    """
    result = await db.execute(
        select(CustomerAccount).where(
            CustomerAccount.store_id == store_id,
            CustomerAccount.email == email,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None or not verify_password(password, customer.hashed_password):
        return None
    if not customer.is_active:
        return None
    return customer


async def get_customer_by_id(
    db: AsyncSession,
    customer_id: uuid.UUID,
    store_id: uuid.UUID | None = None,
) -> CustomerAccount | None:
    """Retrieve a customer by their UUID, optionally scoped to a store.

    Args:
        db: Async database session.
        customer_id: The customer's UUID.
        store_id: Optional store scope.

    Returns:
        The CustomerAccount if found and active, None otherwise.
    """
    query = select(CustomerAccount).where(CustomerAccount.id == customer_id)
    if store_id:
        query = query.where(CustomerAccount.store_id == store_id)
    result = await db.execute(query)
    customer = result.scalar_one_or_none()
    if customer and not customer.is_active:
        return None
    return customer
