"""Customer authentication API router.

Provides registration, login, token refresh, profile management, and
password reset endpoints for storefront customer accounts.

**For Developers:**
    All endpoints are under ``/public/stores/{slug}/customers/``.
    No store-owner authentication is required — these are public-facing
    endpoints consumed by the storefront.

**For QA Engineers:**
    - Registration enforces unique email per store.
    - Login returns access + refresh tokens.
    - Profile endpoints require a valid customer JWT.
    - Password reset uses a time-limited token (1 hour).

**For End Users:**
    Create an account, sign in, manage your profile, and reset your
    password from the storefront.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import CustomerAccount
from app.models.store import Store, StoreStatus
from app.api.deps import get_current_customer
from app.schemas.customer import (
    CustomerChangePasswordRequest,
    CustomerForgotPasswordRequest,
    CustomerLoginRequest,
    CustomerProfileResponse,
    CustomerRefreshRequest,
    CustomerRegisterRequest,
    CustomerResetPasswordRequest,
    CustomerTokenRefreshResponse,
    CustomerTokenResponse,
    CustomerUpdateRequest,
)
from app.services.auth_service import decode_token
from app.services.customer_service import (
    authenticate_customer,
    create_customer_access_token,
    create_customer_refresh_token,
    create_password_reset_token,
    get_customer_by_id,
    hash_password,
    register_customer,
    verify_password,
)

router = APIRouter(prefix="/public/stores/{slug}/customers", tags=["customer-auth"])


async def _get_active_store(db: AsyncSession, slug: str) -> Store:
    """Resolve an active store by slug.

    Args:
        db: Async database session.
        slug: The store's URL slug.

    Returns:
        The Store ORM instance.

    Raises:
        HTTPException: 404 if the store is not found or not active.
    """
    result = await db.execute(
        select(Store).where(Store.slug == slug, Store.status == StoreStatus.active)
    )
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.post(
    "/register",
    response_model=CustomerTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    slug: str,
    body: CustomerRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new customer account for a store.

    Args:
        slug: The store's URL slug.
        body: Registration data (email, password, optional name).
        db: Async database session.

    Returns:
        Access and refresh tokens with customer profile.

    Raises:
        HTTPException: 400 if the email is already taken.
        HTTPException: 404 if the store is not found.
    """
    store = await _get_active_store(db, slug)
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
        raise HTTPException(status_code=400, detail=str(e))

    await db.commit()
    await db.refresh(customer)

    # Send welcome email in the background
    from app.tasks.email_tasks import send_welcome_email
    send_welcome_email.delay(str(customer.id), str(store.id))

    # Notify connected services about the new customer
    from app.services.bridge_service import fire_platform_event
    fire_platform_event(
        user_id=store.user_id,
        store_id=store.id,
        event="customer.created",
        resource_id=customer.id,
        resource_type="customer",
        payload={
            "customer_id": str(customer.id),
            "email": customer.email,
            "first_name": customer.first_name,
            "store_id": str(store.id),
        },
    )

    return CustomerTokenResponse(
        access_token=create_customer_access_token(customer.id, store.id),
        refresh_token=create_customer_refresh_token(customer.id, store.id),
        customer=CustomerProfileResponse.model_validate(customer),
    )


@router.post("/login", response_model=CustomerTokenResponse)
async def login(
    slug: str,
    body: CustomerLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a customer and return tokens.

    Args:
        slug: The store's URL slug.
        body: Login credentials (email, password).
        db: Async database session.

    Returns:
        Access and refresh tokens with customer profile.

    Raises:
        HTTPException: 401 if credentials are invalid.
        HTTPException: 404 if the store is not found.
    """
    store = await _get_active_store(db, slug)
    customer = await authenticate_customer(db, store.id, body.email, body.password)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return CustomerTokenResponse(
        access_token=create_customer_access_token(customer.id, store.id),
        refresh_token=create_customer_refresh_token(customer.id, store.id),
        customer=CustomerProfileResponse.model_validate(customer),
    )


@router.post("/refresh", response_model=CustomerTokenRefreshResponse)
async def refresh_token(
    slug: str,
    body: CustomerRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh a customer access token using a refresh token.

    Args:
        slug: The store's URL slug.
        body: The refresh token.
        db: Async database session.

    Returns:
        A new access token.

    Raises:
        HTTPException: 401 if the refresh token is invalid.
    """
    store = await _get_active_store(db, slug)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )

    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh" or payload.get("aud") != "customer":
            raise credentials_exception
        customer_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise credentials_exception

    customer = await get_customer_by_id(db, customer_id, store.id)
    if not customer:
        raise credentials_exception

    return CustomerTokenRefreshResponse(
        access_token=create_customer_access_token(customer.id, store.id),
    )


@router.get("/me", response_model=CustomerProfileResponse)
async def get_profile(
    customer: CustomerAccount = Depends(get_current_customer),
):
    """Get the authenticated customer's profile.

    Args:
        customer: The current customer (from JWT).

    Returns:
        Customer profile data.
    """
    return CustomerProfileResponse.model_validate(customer)


@router.patch("/me", response_model=CustomerProfileResponse)
async def update_profile(
    body: CustomerUpdateRequest,
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated customer's profile.

    Args:
        body: Fields to update (first_name, last_name, email).
        customer: The current customer (from JWT).
        db: Async database session.

    Returns:
        Updated customer profile.
    """
    if body.first_name is not None:
        customer.first_name = body.first_name
    if body.last_name is not None:
        customer.last_name = body.last_name
    if body.email is not None:
        customer.email = body.email
    await db.commit()
    await db.refresh(customer)
    return CustomerProfileResponse.model_validate(customer)


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: CustomerChangePasswordRequest,
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """Change the authenticated customer's password.

    Args:
        body: Current and new passwords.
        customer: The current customer (from JWT).
        db: Async database session.

    Raises:
        HTTPException: 400 if the current password is incorrect.
    """
    if not verify_password(body.current_password, customer.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    customer.hashed_password = hash_password(body.new_password)
    await db.commit()


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(
    slug: str,
    body: CustomerForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset email.

    Always returns 204 regardless of whether the email exists (to prevent
    email enumeration).

    Args:
        slug: The store's URL slug.
        body: The customer's email address.
        db: Async database session.
    """
    store = await _get_active_store(db, slug)
    result = await db.execute(
        select(CustomerAccount).where(
            CustomerAccount.store_id == store.id,
            CustomerAccount.email == body.email,
        )
    )
    customer = result.scalar_one_or_none()
    if customer:
        _token = create_password_reset_token(customer.id)
        # Send password reset email in the background
        from app.tasks.email_tasks import send_password_reset
        send_password_reset.delay(customer.email, _token, str(store.id))


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    slug: str,
    body: CustomerResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset a customer's password using a reset token.

    Args:
        slug: The store's URL slug.
        body: Reset token and new password.
        db: Async database session.

    Raises:
        HTTPException: 400 if the token is invalid or expired.
    """
    await _get_active_store(db, slug)

    try:
        payload = decode_token(body.token)
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid reset token")
        customer_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    customer = await get_customer_by_id(db, customer_id)
    if not customer:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    customer.hashed_password = hash_password(body.new_password)
    await db.commit()
