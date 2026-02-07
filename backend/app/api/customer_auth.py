"""Customer authentication API router.

Provides endpoints for storefront customer registration, login, token
refresh, and profile management. All endpoints are scoped to a store
by its URL slug.

**For Developers:**
    Mounted at ``/api/v1/public/stores/{slug}/auth``. Uses
    ``customer_auth_service`` for business logic. The ``/register`` and
    ``/login`` endpoints are unauthenticated. ``/me`` requires a valid
    customer access token.

**For QA Engineers:**
    - ``POST /register`` returns 409 if the email already exists on the store.
    - ``POST /login`` returns 401 for invalid credentials.
    - ``POST /refresh`` rejects user tokens and expired tokens.
    - ``GET /me`` and ``PATCH /me`` require customer_access tokens.

**For End Users:**
    Create an account to track your orders and save products to your wishlist.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_current_customer
from app.api.store_lookup import get_active_store
from app.database import get_db
from app.models.customer import Customer
from app.schemas.customer import (
    CustomerLoginRequest,
    CustomerRefreshRequest,
    CustomerRegisterRequest,
    CustomerResponse,
    CustomerTokenResponse,
    CustomerUpdateRequest,
)
from app.services.auth_service import decode_token
from app.services.customer_auth_service import (
    authenticate_customer,
    create_customer_access_token,
    create_customer_refresh_token,
    get_customer_by_id,
    register_customer,
)

router = APIRouter(prefix="/public/stores/{slug}/auth", tags=["customer-auth"])


@router.post(
    "/register",
    response_model=CustomerTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def customer_register(
    slug: str,
    body: CustomerRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> CustomerTokenResponse:
    """Register a new customer account on a store.

    Args:
        slug: The store's URL slug.
        body: Registration data (email, password, optional name).
        db: Async database session.

    Returns:
        CustomerTokenResponse with access and refresh tokens.

    Raises:
        HTTPException: 404 if the store is not found.
        HTTPException: 409 if the email already exists on this store.
    """
    store = await get_active_store(db, slug)

    try:
        customer = await register_customer(
            db,
            store_id=store.id,
            email=body.email,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    # Commit so the customer row is visible when the token is used immediately.
    await db.commit()

    return CustomerTokenResponse(
        access_token=create_customer_access_token(customer.id, store.id),
        refresh_token=create_customer_refresh_token(customer.id, store.id),
    )


@router.post("/login", response_model=CustomerTokenResponse)
async def customer_login(
    slug: str,
    body: CustomerLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> CustomerTokenResponse:
    """Login as a customer on a store.

    Args:
        slug: The store's URL slug.
        body: Login credentials (email, password).
        db: Async database session.

    Returns:
        CustomerTokenResponse with access and refresh tokens.

    Raises:
        HTTPException: 404 if the store is not found.
        HTTPException: 401 if the credentials are invalid.
    """
    store = await get_active_store(db, slug)

    customer = await authenticate_customer(
        db, store_id=store.id, email=body.email, password=body.password
    )
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return CustomerTokenResponse(
        access_token=create_customer_access_token(customer.id, store.id),
        refresh_token=create_customer_refresh_token(customer.id, store.id),
    )


@router.post("/refresh", response_model=CustomerTokenResponse)
async def customer_refresh(
    slug: str,
    body: CustomerRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> CustomerTokenResponse:
    """Refresh customer tokens using a valid refresh token.

    Args:
        slug: The store's URL slug.
        body: The refresh token to exchange.
        db: Async database session.

    Returns:
        CustomerTokenResponse with new access and refresh tokens.

    Raises:
        HTTPException: 401 if the refresh token is invalid.
    """
    store = await get_active_store(db, slug)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )

    try:
        payload = decode_token(body.refresh_token)
        customer_id_str = payload.get("sub")
        token_type = payload.get("type")
        store_id_str = payload.get("store_id")

        if (
            customer_id_str is None
            or token_type != "customer_refresh"
            or store_id_str != str(store.id)
        ):
            raise credentials_exception

        customer_id = uuid.UUID(customer_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    customer = await get_customer_by_id(db, customer_id)
    if customer is None or not customer.is_active:
        raise credentials_exception

    return CustomerTokenResponse(
        access_token=create_customer_access_token(customer.id, store.id),
        refresh_token=create_customer_refresh_token(customer.id, store.id),
    )


@router.get("/me", response_model=CustomerResponse)
async def customer_me(
    customer: Customer = Depends(require_current_customer),
) -> CustomerResponse:
    """Get the current customer's profile.

    Args:
        customer: The authenticated customer.

    Returns:
        CustomerResponse with the customer's profile data.
    """
    return CustomerResponse.model_validate(customer)


@router.patch("/me", response_model=CustomerResponse)
async def customer_update_profile(
    body: CustomerUpdateRequest,
    customer: Customer = Depends(require_current_customer),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Update the current customer's profile.

    Args:
        body: Fields to update (first_name, last_name, phone).
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        CustomerResponse with the updated profile data.
    """
    if body.first_name is not None:
        customer.first_name = body.first_name
    if body.last_name is not None:
        customer.last_name = body.last_name
    if body.phone is not None:
        customer.phone = body.phone

    await db.flush()
    await db.refresh(customer)
    return CustomerResponse.model_validate(customer)
