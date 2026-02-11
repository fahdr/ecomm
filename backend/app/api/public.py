"""Public API router for unauthenticated storefront endpoints.

Provides read-only access to store and product data for the public-facing
storefront. No authentication is required — these endpoints are consumed
by the Next.js storefront app via server-side rendering.

**For Developers:**
    The router is prefixed with ``/public`` (full path:
    ``/api/v1/public/...``). Stores are looked up by slug, not UUID.
    Products are scoped to a store slug and only active products are returned.

**For QA Engineers:**
    - Only stores with ``status == active`` are returned.
    - Only products with ``status == active`` are returned.
    - Paused and deleted stores return 404.
    - No ``user_id`` or ``cost`` is exposed in product responses.

**For End Users:**
    These endpoints power the public storefront. When you visit a store
    URL, the storefront fetches store and product data from here.
"""

import json
import math
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.order import Order
from app.models.product import Product, ProductStatus
from app.models.store import Store, StoreStatus
from app.schemas.order import (
    CalculateTaxRequest,
    CalculateTaxResponse,
    CheckoutRequest,
    CheckoutResponse,
    OrderResponse,
    ValidateDiscountRequest,
    ValidateDiscountResponse,
)
from app.schemas.public import (
    PaginatedPublicProductResponse,
    PublicProductResponse,
    PublicStoreResponse,
)
from app.schemas.theme import PublicThemeResponse
from app.services import order_service, theme_service
from app.services.discount_service import apply_discount, validate_discount
from app.services.gift_card_service import charge_gift_card, validate_gift_card
from app.services.stripe_service import create_checkout_session
from app.services.tax_service import calculate_tax

router = APIRouter(prefix="/public", tags=["public"])


async def _get_active_store(db: AsyncSession, slug: str) -> Store:
    """Retrieve an active store by slug or raise 404.

    Args:
        db: Async database session.
        slug: The store's URL slug.

    Returns:
        The Store ORM instance.

    Raises:
        HTTPException: 404 if the store does not exist or is not active.
    """
    result = await db.execute(
        select(Store).where(Store.slug == slug, Store.status == StoreStatus.active)
    )
    store = result.scalar_one_or_none()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return store


@router.get("/stores/{slug}", response_model=PublicStoreResponse)
async def get_public_store(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> PublicStoreResponse:
    """Retrieve a store by its slug for public display.

    Only active stores are returned. Paused or deleted stores will
    result in a 404 response.

    Args:
        slug: The URL-friendly store slug (e.g. ``my-awesome-store``).
        db: Async database session injected by FastAPI.

    Returns:
        PublicStoreResponse with the store's public-facing data.

    Raises:
        HTTPException: 404 if the store does not exist or is not active.
    """
    store = await _get_active_store(db, slug)
    return PublicStoreResponse.model_validate(store)


@router.get(
    "/stores/{slug}/products",
    response_model=PaginatedPublicProductResponse,
)
async def list_public_products(
    slug: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedPublicProductResponse:
    """List active products for a store (public, paginated).

    Only products with ``status == active`` are returned. The response
    does not include ``cost`` or ``store_id``.

    Args:
        slug: The store's URL slug.
        page: Page number (1-based, default 1).
        per_page: Items per page (1–100, default 20).
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedPublicProductResponse with product items and pagination metadata.

    Raises:
        HTTPException: 404 if the store does not exist or is not active.
    """
    store = await _get_active_store(db, slug)

    base_filter = [
        Product.store_id == store.id,
        Product.status == ProductStatus.active,
    ]

    count_result = await db.execute(
        select(func.count(Product.id)).where(*base_filter)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Product)
        .where(*base_filter)
        .order_by(Product.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    products = list(result.scalars().all())

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedPublicProductResponse(
        items=[PublicProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/stores/{slug}/products/{product_slug}",
    response_model=PublicProductResponse,
)
async def get_public_product(
    slug: str,
    product_slug: str,
    db: AsyncSession = Depends(get_db),
) -> PublicProductResponse:
    """Retrieve a single active product by its slug (public).

    Args:
        slug: The store's URL slug.
        product_slug: The product's URL slug.
        db: Async database session injected by FastAPI.

    Returns:
        PublicProductResponse with the product's public-facing data.

    Raises:
        HTTPException: 404 if the store or product does not exist or is not active.
    """
    store = await _get_active_store(db, slug)

    result = await db.execute(
        select(Product).where(
            Product.store_id == store.id,
            Product.slug == product_slug,
            Product.status == ProductStatus.active,
        )
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return PublicProductResponse.model_validate(product)


@router.post(
    "/stores/{slug}/checkout/validate-discount",
    response_model=ValidateDiscountResponse,
)
async def validate_discount_endpoint(
    slug: str,
    body: ValidateDiscountRequest,
    db: AsyncSession = Depends(get_db),
) -> ValidateDiscountResponse:
    """Validate a discount code for a store before checkout.

    Checks the code's validity, expiry, usage limits, and minimum order
    amount, then returns the calculated discount for the given subtotal.
    Use this endpoint to show real-time discount previews on the
    storefront checkout page.

    Args:
        slug: The store's URL slug.
        body: Discount validation request with code and subtotal.
        db: Async database session injected by FastAPI.

    Returns:
        ValidateDiscountResponse with validity, discount amount, and message.

    Raises:
        HTTPException: 404 if the store doesn't exist or is not active.
    """
    store = await _get_active_store(db, slug)
    result = await validate_discount(
        db=db,
        store_id=store.id,
        code=body.code,
        subtotal=body.subtotal,
        product_ids=body.product_ids,
    )
    return ValidateDiscountResponse(
        valid=result["valid"],
        discount_type=result.get("discount_type"),
        value=result.get("value"),
        discount_amount=result.get("discount_amount", Decimal("0.00")),
        message=result.get("message", ""),
    )


@router.post(
    "/stores/{slug}/checkout/calculate-tax",
    response_model=CalculateTaxResponse,
)
async def calculate_tax_endpoint(
    slug: str,
    body: CalculateTaxRequest,
    db: AsyncSession = Depends(get_db),
) -> CalculateTaxResponse:
    """Calculate tax for a store checkout based on shipping address.

    Finds matching tax rates for the customer's address and calculates
    the total tax. Use this endpoint to show real-time tax estimates
    on the storefront checkout page.

    Args:
        slug: The store's URL slug.
        body: Tax calculation request with subtotal and address fields.
        db: Async database session injected by FastAPI.

    Returns:
        CalculateTaxResponse with tax amount, effective rate, and breakdown.

    Raises:
        HTTPException: 404 if the store doesn't exist or is not active.
    """
    store = await _get_active_store(db, slug)
    result = await calculate_tax(
        db=db,
        store_id=store.id,
        subtotal=body.subtotal,
        country=body.country,
        state=body.state,
        zip_code=body.postal_code,
    )
    return CalculateTaxResponse(
        tax_amount=result["tax_amount"],
        effective_rate=result["effective_rate"],
        breakdown=result.get("breakdown", []),
    )


@router.post(
    "/stores/{slug}/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout(
    slug: str,
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Create a checkout session for a store.

    Validates cart items, applies discount codes, calculates tax from
    the shipping address, deducts gift card balance, creates a pending
    order with full financial breakdown, and returns a Stripe Checkout
    URL for the customer to complete payment.

    **Flow:**
        1. Validate cart items (products exist, in stock, correct store).
        2. If ``discount_code`` provided, validate and calculate discount.
        3. Calculate tax based on shipping address and discounted subtotal.
        4. If ``gift_card_code`` provided, validate and calculate deduction.
        5. Compute final total: subtotal - discount + tax - gift_card.
        6. Create Stripe Checkout session for the final total.
        7. Create pending order with all financial data and shipping address.

    Args:
        slug: The store's URL slug.
        body: Checkout request with email, items, shipping address,
            and optional discount/gift card codes.
        db: Async database session injected by FastAPI.

    Returns:
        CheckoutResponse with checkout URL, session ID, order ID,
        and full financial breakdown.

    Raises:
        HTTPException: 404 if the store doesn't exist or is not active.
        HTTPException: 400 if cart items are invalid, discount code is
            invalid, or gift card has insufficient balance.
    """
    store = await _get_active_store(db, slug)

    # 1. Validate cart items
    items = [
        {
            "product_id": item.product_id,
            "variant_id": item.variant_id,
            "quantity": item.quantity,
        }
        for item in body.items
    ]

    try:
        order_items, subtotal = await order_service.validate_and_build_order_items(
            db, store.id, items
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 2. Apply discount code (if provided)
    discount_amount = Decimal("0.00")
    discount_code = None
    if body.discount_code:
        product_ids = [item.product_id for item in body.items]
        discount_result = await validate_discount(
            db=db,
            store_id=store.id,
            code=body.discount_code,
            subtotal=subtotal,
            product_ids=product_ids,
        )
        if not discount_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=discount_result["message"],
            )
        discount_amount = discount_result["discount_amount"]
        discount_code = body.discount_code.upper()

    discounted_subtotal = max(subtotal - discount_amount, Decimal("0.00"))

    # 3. Calculate tax from shipping address
    tax_amount = Decimal("0.00")
    addr = body.shipping_address
    tax_result = await calculate_tax(
        db=db,
        store_id=store.id,
        subtotal=discounted_subtotal,
        country=addr.country,
        state=addr.state,
        zip_code=addr.postal_code,
    )
    tax_amount = tax_result["tax_amount"]

    # 4. Apply gift card (if provided)
    gift_card_amount = Decimal("0.00")
    if body.gift_card_code:
        gc_result = await validate_gift_card(
            db=db,
            store_id=store.id,
            code=body.gift_card_code,
        )
        if not gc_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=gc_result["message"],
            )
        # Deduct up to the remaining total (don't overshoot)
        remaining = discounted_subtotal + tax_amount
        gift_card_amount = min(gc_result["balance"], remaining)

    # 5. Compute final total
    total = max(discounted_subtotal + tax_amount - gift_card_amount, Decimal("0.00"))

    # 6. Create Stripe session (for the amount Stripe will charge)
    checkout_id = uuid.uuid4()
    stripe_data = create_checkout_session(
        order_id=checkout_id,
        items=order_items,
        customer_email=body.customer_email,
        store_name=store.name,
        total_override=total if (discount_amount > 0 or gift_card_amount > 0 or tax_amount > 0) else None,
    )

    # 7. Create pending order with full financial breakdown
    shipping_address_json = json.dumps(body.shipping_address.model_dump())

    order = await order_service.create_order_from_checkout(
        db=db,
        store_id=store.id,
        customer_email=body.customer_email,
        items_data=order_items,
        total=total,
        stripe_session_id=stripe_data["session_id"],
        subtotal=subtotal,
        shipping_address=shipping_address_json,
        discount_code=discount_code,
        discount_amount=discount_amount,
        tax_amount=tax_amount,
        gift_card_amount=gift_card_amount,
    )

    return CheckoutResponse(
        checkout_url=stripe_data["checkout_url"],
        session_id=stripe_data["session_id"],
        order_id=order.id,
        subtotal=subtotal,
        discount_amount=discount_amount,
        tax_amount=tax_amount,
        gift_card_amount=gift_card_amount,
        total=total,
    )


@router.get(
    "/stores/{slug}/orders/{order_id}",
    response_model=OrderResponse,
)
async def get_public_order(
    slug: str,
    order_id: str,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Retrieve an order by ID for the order confirmation page.

    This public endpoint allows customers to view their order status
    after checkout without requiring authentication.

    Args:
        slug: The store's URL slug.
        order_id: The order's UUID.
        db: Async database session injected by FastAPI.

    Returns:
        OrderResponse with the order data and items.

    Raises:
        HTTPException: 404 if the store or order doesn't exist.
    """
    store = await _get_active_store(db, slug)

    import uuid as uuid_mod
    try:
        oid = uuid_mod.UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    result = await db.execute(
        select(Order).where(
            Order.id == oid,
            Order.store_id == store.id,
        )
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return OrderResponse.from_order(order)


@router.get("/stores/{slug}/theme", response_model=PublicThemeResponse)
async def get_public_theme(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> PublicThemeResponse:
    """Retrieve the active theme for a store (public, no auth required).

    The storefront uses this endpoint to load colors, fonts, styles,
    and page blocks for rendering. Returns the currently active theme.

    Args:
        slug: The store's URL slug.
        db: Async database session injected by FastAPI.

    Returns:
        PublicThemeResponse with colors, typography, styles, blocks, and logo.

    Raises:
        HTTPException: 404 if the store doesn't exist, is not active,
            or has no active theme.
    """
    store = await _get_active_store(db, slug)
    theme = await theme_service.get_active_theme(db, store.id)
    if theme is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active theme found",
        )
    return PublicThemeResponse.model_validate(theme)
