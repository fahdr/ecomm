"""Shared FastAPI dependencies for API routes.

Provides reusable dependencies such as ``get_current_user`` that can be
injected into any route handler that requires an authenticated user,
and plan enforcement dependencies (``check_store_limit``,
``check_product_limit``) that gate resource creation.

**For Developers:**
    Use ``current_user: User = Depends(get_current_user)`` in route
    signatures to enforce authentication and receive the caller's User object.
    Use ``Depends(check_store_limit)`` / ``Depends(check_product_limit)``
    on create endpoints to enforce plan limits (returns 403 if exceeded).

**For QA Engineers:**
    - Any request missing a valid ``Authorization: Bearer <token>`` header
      will receive a 401 response with ``"Could not validate credentials"``.
    - Plan limit violations return 403 with a message indicating the limit
      and suggesting an upgrade.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PlanTier, get_plan_limits
from app.database import get_db
from app.models.customer import Customer
from app.models.product import Product, ProductStatus
from app.models.store import Store, StoreStatus
from app.models.user import User
from app.services.auth_service import decode_token, get_user_by_id
from app.services.customer_auth_service import get_customer_by_id

# OAuth2 scheme extracts the Bearer token from the Authorization header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Optional OAuth2 scheme for customer tokens (auto_error=False so guests pass through)
customer_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/public/stores/{slug}/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency that resolves the current authenticated user.

    Extracts the JWT from the ``Authorization: Bearer`` header, decodes it,
    and loads the corresponding user from the database.

    Args:
        token: The JWT access token, automatically extracted by OAuth2PasswordBearer.
        db: Async database session injected by FastAPI.

    Returns:
        The authenticated User ORM instance.

    Raises:
        HTTPException: 401 if the token is invalid, expired, not an access token,
            or the user does not exist / is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id_str: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id_str is None or token_type != "access":
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def check_store_limit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Verify the user has not exceeded their plan's store limit.

    Inject this instead of ``get_current_user`` on store creation
    endpoints. Returns the authenticated user on success.

    Args:
        current_user: The authenticated user (resolved via ``get_current_user``).
        db: Async database session.

    Returns:
        The authenticated User if within limits.

    Raises:
        HTTPException: 403 if the user has reached their store limit.
    """
    limits = get_plan_limits(PlanTier(current_user.plan))
    if limits.max_stores == -1:
        return current_user

    result = await db.execute(
        select(func.count(Store.id)).where(
            Store.user_id == current_user.id,
            Store.status != StoreStatus.deleted,
        )
    )
    count = result.scalar_one()

    if count >= limits.max_stores:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Plan limit reached: {limits.max_stores} store(s) allowed "
                f"on the {current_user.plan.value} plan. Upgrade to create more."
            ),
        )
    return current_user


async def check_product_limit(
    store_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Verify the user has not exceeded their plan's per-store product limit.

    Inject this instead of ``get_current_user`` on product creation
    endpoints. Returns the authenticated user on success.

    Args:
        store_id: The store UUID (from the URL path).
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        The authenticated User if within limits.

    Raises:
        HTTPException: 403 if the product limit for the store is reached.
    """
    limits = get_plan_limits(PlanTier(current_user.plan))
    if limits.max_products_per_store == -1:
        return current_user

    result = await db.execute(
        select(func.count(Product.id)).where(
            Product.store_id == store_id,
            Product.status != ProductStatus.archived,
        )
    )
    count = result.scalar_one()

    if count >= limits.max_products_per_store:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Plan limit reached: {limits.max_products_per_store} product(s) "
                f"per store allowed on the {current_user.plan.value} plan. "
                f"Upgrade to add more."
            ),
        )
    return current_user


async def get_current_customer(
    token: str | None = Depends(customer_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Customer | None:
    """Resolve the current customer from a JWT, or return None for guests.

    Checks ``type == "customer_access"``, loads Customer from the database.
    Returns None if no token is provided or the token is invalid (guest mode).

    **For Developers:**
        Use this dependency on endpoints that optionally support customers
        (e.g. checkout). For required auth, use ``require_current_customer``.

    Args:
        token: Optional JWT access token extracted by the customer OAuth2 scheme.
        db: Async database session.

    Returns:
        The Customer instance if authenticated, or None for guests.
    """
    if token is None:
        return None

    try:
        payload = decode_token(token)
        customer_id_str: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if customer_id_str is None or token_type != "customer_access":
            return None
        customer_id = uuid.UUID(customer_id_str)
    except (JWTError, ValueError):
        return None

    customer = await get_customer_by_id(db, customer_id)
    if customer is None or not customer.is_active:
        return None

    return customer


async def require_current_customer(
    customer: Customer | None = Depends(get_current_customer),
) -> Customer:
    """Like ``get_current_customer`` but raises 401 if not authenticated.

    **For Developers:**
        Use this on endpoints that require customer authentication
        (order history, wishlist, profile).

    Args:
        customer: The optionally resolved customer.

    Returns:
        The authenticated Customer instance.

    Raises:
        HTTPException: 401 if no valid customer token was provided.
    """
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return customer
