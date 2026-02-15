"""Discount business logic.

Handles CRUD operations for store-level promotional discounts, validation
of discount codes at checkout, and recording of discount usage for audit
and analytics purposes.

**For Developers:**
    All functions take ``store_id`` and ``user_id`` to enforce store
    ownership for admin operations. The ``validate_discount`` and
    ``apply_discount`` functions are used during checkout and do not
    require ownership verification (they operate on behalf of customers).
    Discounts support three targeting modes: all products, specific
    products, or specific categories.

**For QA Engineers:**
    - ``create_discount`` normalises the code to uppercase.
    - ``validate_discount`` checks expiry, max uses, minimum order amount,
      and product/category targeting before approving a code.
    - ``apply_discount`` increments ``times_used`` and creates a
      ``DiscountUsage`` audit record.
    - ``list_discounts`` supports optional status filtering and pagination.
    - ``delete_discount`` is a hard delete (not soft-delete).

**For Project Managers:**
    This service powers Feature 8 (Discounts & Coupons) from the backlog.
    It enables store owners to create time-limited promotional codes with
    flexible targeting and usage caps, and provides checkout-time validation.

**For End Users:**
    Create coupon codes for your store that customers can enter at checkout
    to receive percentage or fixed-amount discounts. Set minimum order
    amounts, usage limits, and validity windows to control promotions.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discount import (
    AppliesTo,
    Discount,
    DiscountCategory,
    DiscountProduct,
    DiscountStatus,
    DiscountType,
    DiscountUsage,
)
from app.models.store import Store, StoreStatus


async def _verify_store_ownership(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> Store:
    """Verify that a store exists and belongs to the given user.

    Args:
        db: Async database session.
        store_id: The UUID of the store.
        user_id: The requesting user's UUID.

    Returns:
        The Store ORM instance.

    Raises:
        ValueError: If the store doesn't exist, is deleted, or belongs
            to a different user.
    """
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted:
        raise ValueError("Store not found")
    if store.user_id != user_id:
        raise ValueError("Store not found")
    return store


async def create_discount(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    code: str,
    description: str | None,
    discount_type: DiscountType,
    value: Decimal,
    minimum_order_amount: Decimal | None = None,
    max_uses: int | None = None,
    starts_at: datetime | None = None,
    expires_at: datetime | None = None,
    applies_to: AppliesTo = AppliesTo.all,
    product_ids: list[uuid.UUID] | None = None,
    category_ids: list[uuid.UUID] | None = None,
) -> Discount:
    """Create a new discount code for a store.

    Normalises the coupon code to uppercase and optionally links the
    discount to specific products or categories depending on the
    ``applies_to`` targeting mode.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        code: The coupon code string (will be uppercased).
        description: Optional human-readable promotion description.
        discount_type: The calculation method (percentage, fixed_amount,
            or free_shipping).
        value: The numeric discount value.
        minimum_order_amount: Optional minimum cart subtotal required.
        max_uses: Optional cap on total redemptions.
        starts_at: When the discount becomes active (defaults to now).
        expires_at: Optional expiry date/time.
        applies_to: Targeting scope (all, specific_products, specific_categories).
        product_ids: List of product UUIDs when targeting specific products.
        category_ids: List of category UUIDs when targeting specific categories.

    Returns:
        The newly created Discount ORM instance with relationships loaded.

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            or a discount with the same code already exists in this store.
    """
    await _verify_store_ownership(db, store_id, user_id)

    # Check for duplicate code within the store
    existing = await db.execute(
        select(Discount).where(
            Discount.store_id == store_id,
            Discount.code == code.upper(),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError(f"A discount with code '{code.upper()}' already exists in this store")

    discount = Discount(
        store_id=store_id,
        code=code.upper(),
        description=description,
        discount_type=discount_type,
        value=value,
        minimum_order_amount=minimum_order_amount,
        max_uses=max_uses,
        starts_at=starts_at or datetime.now(timezone.utc),
        expires_at=expires_at,
        applies_to=applies_to,
        status=DiscountStatus.active,
    )
    db.add(discount)
    await db.flush()

    # Link to specific products if applicable
    if applies_to == AppliesTo.specific_products and product_ids:
        for pid in product_ids:
            db.add(DiscountProduct(discount_id=discount.id, product_id=pid))
        await db.flush()

    # Link to specific categories if applicable
    if applies_to == AppliesTo.specific_categories and category_ids:
        for cid in category_ids:
            db.add(DiscountCategory(discount_id=discount.id, category_id=cid))
        await db.flush()

    await db.refresh(discount)
    return discount


async def list_discounts(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    status_filter: DiscountStatus | None = None,
) -> tuple[list[Discount], int]:
    """List discounts for a store with pagination and optional status filtering.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        page: Page number (1-based).
        per_page: Number of items per page.
        status_filter: Optional status to filter by (active, expired, disabled).

    Returns:
        A tuple of (discounts list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    query = select(Discount).where(Discount.store_id == store_id)
    count_query = select(func.count(Discount.id)).where(Discount.store_id == store_id)

    if status_filter is not None:
        query = query.where(Discount.status == status_filter)
        count_query = count_query.where(Discount.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Discount.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    discounts = list(result.scalars().all())

    return discounts, total


async def get_discount(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    discount_id: uuid.UUID,
) -> Discount:
    """Retrieve a single discount, verifying store ownership.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        discount_id: The UUID of the discount to retrieve.

    Returns:
        The Discount ORM instance with relationships loaded.

    Raises:
        ValueError: If the store or discount doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(Discount).where(
            Discount.id == discount_id,
            Discount.store_id == store_id,
        )
    )
    discount = result.scalar_one_or_none()
    if discount is None:
        raise ValueError("Discount not found")
    return discount


async def update_discount(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    discount_id: uuid.UUID,
    **kwargs,
) -> Discount:
    """Update a discount's fields (partial update).

    Only provided (non-None) keyword arguments are applied to the
    discount record. The ``product_ids`` and ``category_ids`` kwargs
    are handled specially to replace the many-to-many links.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        discount_id: The UUID of the discount to update.
        **kwargs: Keyword arguments for fields to update.

    Returns:
        The updated Discount ORM instance.

    Raises:
        ValueError: If the store or discount doesn't exist, or the store
            belongs to another user.
    """
    discount = await get_discount(db, store_id, user_id, discount_id)

    product_ids = kwargs.pop("product_ids", None)
    category_ids = kwargs.pop("category_ids", None)

    for key, value in kwargs.items():
        if value is not None:
            if key == "code":
                value = value.upper()
            setattr(discount, key, value)

    # Replace product links if provided
    if product_ids is not None:
        await db.execute(
            select(DiscountProduct).where(DiscountProduct.discount_id == discount.id)
        )
        # Delete existing links
        existing_links = await db.execute(
            select(DiscountProduct).where(DiscountProduct.discount_id == discount.id)
        )
        for link in existing_links.scalars().all():
            await db.delete(link)
        await db.flush()

        for pid in product_ids:
            db.add(DiscountProduct(discount_id=discount.id, product_id=pid))

    # Replace category links if provided
    if category_ids is not None:
        existing_links = await db.execute(
            select(DiscountCategory).where(DiscountCategory.discount_id == discount.id)
        )
        for link in existing_links.scalars().all():
            await db.delete(link)
        await db.flush()

        for cid in category_ids:
            db.add(DiscountCategory(discount_id=discount.id, category_id=cid))

    await db.flush()
    await db.refresh(discount)
    return discount


async def delete_discount(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    discount_id: uuid.UUID,
) -> None:
    """Permanently delete a discount and all associated records.

    Cascade deletes will remove linked DiscountProduct, DiscountCategory,
    and DiscountUsage records.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        discount_id: The UUID of the discount to delete.

    Raises:
        ValueError: If the store or discount doesn't exist, or the store
            belongs to another user.
    """
    discount = await get_discount(db, store_id, user_id, discount_id)
    await db.delete(discount)
    await db.flush()


async def validate_discount(
    db: AsyncSession,
    store_id: uuid.UUID,
    code: str,
    subtotal: Decimal,
    product_ids: list[uuid.UUID] | None = None,
) -> dict:
    """Validate a discount code for use at checkout.

    Runs a series of business-rule checks to determine whether the code
    is currently valid and calculates the discount amount. This function
    does NOT require store ownership -- it is called on behalf of a
    customer during checkout.

    Validation checks performed:
        1. Code exists and belongs to the store.
        2. Discount status is active (not disabled).
        3. Current time is within the starts_at / expires_at window.
        4. Usage count has not reached max_uses.
        5. Cart subtotal meets minimum_order_amount.
        6. If targeting specific products/categories, at least one cart
           item matches.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        code: The coupon code to validate (case-insensitive).
        subtotal: The current cart subtotal for minimum-order checks.
        product_ids: Optional list of product UUIDs in the cart for
            product/category targeting checks.

    Returns:
        A dict with keys: ``valid`` (bool), ``discount_type``,
        ``value``, ``discount_amount``, and ``message``.
    """
    result = await db.execute(
        select(Discount).where(
            Discount.store_id == store_id,
            Discount.code == code.upper(),
        )
    )
    discount = result.scalar_one_or_none()

    if discount is None:
        return {
            "valid": False,
            "discount_type": None,
            "value": None,
            "discount_amount": Decimal("0.00"),
            "message": "Invalid discount code",
        }

    # Check status
    if discount.status != DiscountStatus.active:
        return {
            "valid": False,
            "discount_type": discount.discount_type,
            "value": discount.value,
            "discount_amount": Decimal("0.00"),
            "message": "This discount code is no longer active",
        }

    now = datetime.now(timezone.utc)

    # Check start date
    if discount.starts_at and now < discount.starts_at:
        return {
            "valid": False,
            "discount_type": discount.discount_type,
            "value": discount.value,
            "discount_amount": Decimal("0.00"),
            "message": "This discount code is not yet active",
        }

    # Check expiry
    if discount.expires_at and now > discount.expires_at:
        return {
            "valid": False,
            "discount_type": discount.discount_type,
            "value": discount.value,
            "discount_amount": Decimal("0.00"),
            "message": "This discount code has expired",
        }

    # Check max uses
    if discount.max_uses is not None and discount.times_used >= discount.max_uses:
        return {
            "valid": False,
            "discount_type": discount.discount_type,
            "value": discount.value,
            "discount_amount": Decimal("0.00"),
            "message": "This discount code has reached its usage limit",
        }

    # Check minimum order amount
    if discount.minimum_order_amount and subtotal < discount.minimum_order_amount:
        return {
            "valid": False,
            "discount_type": discount.discount_type,
            "value": discount.value,
            "discount_amount": Decimal("0.00"),
            "message": (
                f"Minimum order amount of ${discount.minimum_order_amount} "
                f"required for this discount"
            ),
        }

    # Check product/category targeting
    if discount.applies_to == AppliesTo.specific_products and product_ids:
        linked_product_ids_result = await db.execute(
            select(DiscountProduct.product_id).where(
                DiscountProduct.discount_id == discount.id
            )
        )
        linked_product_ids = {row[0] for row in linked_product_ids_result.fetchall()}
        if not linked_product_ids.intersection(set(product_ids)):
            return {
                "valid": False,
                "discount_type": discount.discount_type,
                "value": discount.value,
                "discount_amount": Decimal("0.00"),
                "message": "This discount does not apply to the products in your cart",
            }

    if discount.applies_to == AppliesTo.specific_categories and product_ids:
        from app.models.category import ProductCategory

        linked_cat_ids_result = await db.execute(
            select(DiscountCategory.category_id).where(
                DiscountCategory.discount_id == discount.id
            )
        )
        linked_cat_ids = {row[0] for row in linked_cat_ids_result.fetchall()}

        product_cat_result = await db.execute(
            select(ProductCategory.product_id).where(
                ProductCategory.category_id.in_(linked_cat_ids),
                ProductCategory.product_id.in_(product_ids),
            )
        )
        if not product_cat_result.fetchall():
            return {
                "valid": False,
                "discount_type": discount.discount_type,
                "value": discount.value,
                "discount_amount": Decimal("0.00"),
                "message": "This discount does not apply to the categories in your cart",
            }

    # Calculate discount amount
    discount_amount = _calculate_discount_amount(discount, subtotal)

    return {
        "valid": True,
        "discount_type": discount.discount_type,
        "value": discount.value,
        "discount_amount": discount_amount,
        "message": "Discount applied successfully",
    }


def _calculate_discount_amount(discount: Discount, subtotal: Decimal) -> Decimal:
    """Calculate the actual monetary discount for a given subtotal.

    Args:
        discount: The Discount ORM instance.
        subtotal: The cart subtotal to apply the discount against.

    Returns:
        The calculated discount amount, capped at the subtotal to prevent
        negative totals. Free-shipping discounts return zero (handled
        separately in the checkout flow).
    """
    if discount.discount_type == DiscountType.percentage:
        amount = subtotal * (discount.value / Decimal("100"))
        return min(amount, subtotal)
    elif discount.discount_type == DiscountType.fixed_amount:
        return min(discount.value, subtotal)
    elif discount.discount_type == DiscountType.free_shipping:
        return Decimal("0.00")
    return Decimal("0.00")


async def apply_discount(
    db: AsyncSession,
    store_id: uuid.UUID,
    code: str,
    order_id: uuid.UUID,
    customer_email: str,
    amount_saved: Decimal,
) -> DiscountUsage:
    """Record the application of a discount to an order.

    Increments the discount's ``times_used`` counter and creates a
    ``DiscountUsage`` audit record. Should be called after
    ``validate_discount`` confirms the code is valid and after the
    order has been created.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        code: The coupon code that was used (case-insensitive).
        order_id: The UUID of the order the discount was applied to.
        customer_email: Email of the customer who used the discount.
        amount_saved: The monetary amount deducted by the discount.

    Returns:
        The newly created DiscountUsage audit record.

    Raises:
        ValueError: If the discount code is not found in the store.
    """
    result = await db.execute(
        select(Discount).where(
            Discount.store_id == store_id,
            Discount.code == code.upper(),
        )
    )
    discount = result.scalar_one_or_none()
    if discount is None:
        raise ValueError("Discount code not found")

    # Increment usage counter
    discount.times_used += 1

    # Create usage audit record
    usage = DiscountUsage(
        discount_id=discount.id,
        order_id=order_id,
        customer_email=customer_email,
        amount_saved=amount_saved,
    )
    db.add(usage)
    await db.flush()
    await db.refresh(usage)
    return usage
