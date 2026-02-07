"""Customer authentication business logic.

Handles password hashing, JWT creation/validation, customer registration,
and credential verification for per-store customer accounts. This module
parallels ``auth_service`` but operates on the ``Customer`` model and uses
distinct JWT token types to prevent cross-contamination with User tokens.

**For Developers:**
    - Reuses ``hash_password``, ``verify_password``, and ``decode_token``
      from ``auth_service`` (same bcrypt + HS256 setup).
    - Customer tokens include ``type="customer_access"`` and a ``store_id``
      claim to scope tokens to a single store.
    - All database operations are async.

**For QA Engineers:**
    - Customer tokens are rejected by ``get_current_user`` (type mismatch).
    - User tokens are rejected by ``get_current_customer`` (type mismatch).
    - Duplicate registration on the same store returns ValueError.
    - Same email on different stores is allowed.

**For End Users:**
    Create an account on your favourite store to track orders and manage
    your wishlist.
"""

import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.customer import Customer
from app.services.auth_service import hash_password, verify_password


def create_customer_access_token(
    customer_id: uuid.UUID, store_id: uuid.UUID
) -> str:
    """Create a short-lived JWT access token for a customer.

    Args:
        customer_id: The customer's UUID.
        store_id: The store UUID to embed in the token.

    Returns:
        An encoded JWT string with ``sub``, ``store_id``, ``exp``,
        and ``type`` claims.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": str(customer_id),
        "store_id": str(store_id),
        "type": "customer_access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_customer_refresh_token(
    customer_id: uuid.UUID, store_id: uuid.UUID
) -> str:
    """Create a long-lived JWT refresh token for a customer.

    Args:
        customer_id: The customer's UUID.
        store_id: The store UUID to embed in the token.

    Returns:
        An encoded JWT string with ``sub``, ``store_id``, ``exp``,
        and ``type`` claims.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": str(customer_id),
        "store_id": str(store_id),
        "type": "customer_refresh",
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
) -> Customer:
    """Register a new customer account scoped to a store.

    Args:
        db: Async database session.
        store_id: The store UUID.
        email: The customer's email address.
        password: Plain-text password to hash and store.
        first_name: Optional first name.
        last_name: Optional last name.

    Returns:
        The newly created Customer ORM instance.

    Raises:
        ValueError: If a customer with the given email already exists
            on this store.
    """
    result = await db.execute(
        select(Customer).where(
            Customer.store_id == store_id,
            Customer.email == email,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise ValueError("A customer with this email already exists on this store")

    customer = Customer(
        store_id=store_id,
        email=email,
        hashed_password=hash_password(password),
        first_name=first_name,
        last_name=last_name,
    )
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return customer


async def authenticate_customer(
    db: AsyncSession,
    store_id: uuid.UUID,
    email: str,
    password: str,
) -> Customer | None:
    """Authenticate a customer by store, email, and password.

    Args:
        db: Async database session.
        store_id: The store UUID to scope the lookup.
        email: The email address to look up.
        password: The plain-text password to verify.

    Returns:
        The Customer instance if credentials are valid, or None.
    """
    result = await db.execute(
        select(Customer).where(
            Customer.store_id == store_id,
            Customer.email == email,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None or not verify_password(password, customer.hashed_password):
        return None
    return customer


async def get_customer_by_id(
    db: AsyncSession, customer_id: uuid.UUID
) -> Customer | None:
    """Retrieve a customer by their UUID.

    Args:
        db: Async database session.
        customer_id: The UUID of the customer.

    Returns:
        The Customer instance if found, or None.
    """
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    return result.scalar_one_or_none()
