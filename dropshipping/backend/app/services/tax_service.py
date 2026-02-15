"""Tax business logic.

Handles CRUD operations for store tax rates and tax calculation at
checkout. Tax rates are scoped to geographic regions (country, state,
zip code) and support priority ordering and compound calculation.

**For Developers:**
    Tax rates are matched by geographic specificity: zip code is the most
    specific, then state, then country. The ``priority`` field determines
    the order of application when multiple rates match. Compound tax rates
    are applied on top of the subtotal plus previously applied taxes
    (rather than on the base subtotal alone).

**For QA Engineers:**
    - ``create_tax_rate`` validates that the rate is non-negative.
    - ``calculate_tax`` finds matching tax rates by geographic hierarchy
      and applies them in priority order.
    - Compound rates accumulate on the running total (subtotal + prior taxes).
    - Non-compound rates are applied on the original subtotal only.
    - The breakdown includes each applied rate and its contribution.

**For Project Managers:**
    This service powers Feature 16 (Tax Calculation) from the backlog.
    It allows store owners to define tax rates per region and have taxes
    automatically calculated during checkout.

**For End Users:**
    Set up tax rates for the regions you sell to. Taxes are automatically
    calculated at checkout based on the customer's shipping address.
    You can create multiple rates for different jurisdictions and control
    the order of application.
"""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store, StoreStatus


# ---------------------------------------------------------------------------
# Tax rate model placeholder -- models are being created by another agent.
# We import conditionally and define a lightweight stand-in if not yet
# available. In production the model import will succeed.
# ---------------------------------------------------------------------------
try:
    from app.models.tax import TaxRate
except ImportError:
    # Stand-in for type hints while the model file is being created.
    TaxRate = None  # type: ignore[assignment,misc]


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


async def create_tax_rate(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    rate: Decimal,
    country: str,
    state: str | None = None,
    zip_code: str | None = None,
    priority: int = 0,
    is_inclusive: bool = False,
) -> "TaxRate":
    """Create a new tax rate for a store.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        name: Display name of the tax rate (e.g. "CA Sales Tax").
        rate: Tax rate as a percentage (e.g. 8.25 for 8.25%).
        country: Two-letter ISO country code (e.g. "US").
        state: Optional state/province code (e.g. "CA").
        zip_code: Optional postal/zip code for granular targeting.
        priority: Application order when multiple rates match (lower = first).
        is_inclusive: Whether to apply this rate on the subtotal plus
            previously applied taxes.

    Returns:
        The newly created TaxRate ORM instance.

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            or the rate is negative.
    """
    await _verify_store_ownership(db, store_id, user_id)

    if rate < Decimal("0"):
        raise ValueError("Tax rate cannot be negative")

    tax_rate = TaxRate(
        store_id=store_id,
        name=name,
        rate=rate,
        country=country.upper(),
        state=state.upper() if state else None,
        zip_code=zip_code,
        priority=priority,
        is_inclusive=is_inclusive,
        is_active=True,
    )
    db.add(tax_rate)
    await db.flush()
    await db.refresh(tax_rate)
    return tax_rate


async def list_tax_rates(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list:
    """List all tax rates for a store.

    Returns all tax rates regardless of active status, ordered by
    priority then name.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        A list of TaxRate ORM instances.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(TaxRate)
        .where(TaxRate.store_id == store_id)
        .order_by(TaxRate.priority, TaxRate.name)
    )
    return list(result.scalars().all())


async def update_tax_rate(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    tax_rate_id: uuid.UUID,
    **kwargs,
) -> "TaxRate":
    """Update a tax rate's fields (partial update).

    Only provided (non-None) keyword arguments are applied.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        tax_rate_id: The UUID of the tax rate to update.
        **kwargs: Keyword arguments for fields to update (name, rate,
            country, state, zip_code, priority, is_inclusive, is_active).

    Returns:
        The updated TaxRate ORM instance.

    Raises:
        ValueError: If the store or tax rate doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(TaxRate).where(
            TaxRate.id == tax_rate_id,
            TaxRate.store_id == store_id,
        )
    )
    tax_rate = result.scalar_one_or_none()
    if tax_rate is None:
        raise ValueError("Tax rate not found")

    for key, value in kwargs.items():
        if value is not None:
            if key == "country":
                value = value.upper()
            elif key == "state" and isinstance(value, str):
                value = value.upper()
            setattr(tax_rate, key, value)

    await db.flush()
    await db.refresh(tax_rate)
    return tax_rate


async def delete_tax_rate(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    tax_rate_id: uuid.UUID,
) -> None:
    """Permanently delete a tax rate.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        tax_rate_id: The UUID of the tax rate to delete.

    Raises:
        ValueError: If the store or tax rate doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(TaxRate).where(
            TaxRate.id == tax_rate_id,
            TaxRate.store_id == store_id,
        )
    )
    tax_rate = result.scalar_one_or_none()
    if tax_rate is None:
        raise ValueError("Tax rate not found")

    await db.delete(tax_rate)
    await db.flush()


async def calculate_tax(
    db: AsyncSession,
    store_id: uuid.UUID,
    subtotal: Decimal,
    country: str,
    state: str | None = None,
    zip_code: str | None = None,
) -> dict:
    """Calculate applicable taxes for an order.

    Finds matching active tax rates by geographic hierarchy (most specific
    first: zip > state > country) and applies them in priority order.
    Compound rates are applied on the running total; non-compound rates
    are applied on the original subtotal.

    This function does NOT require store ownership verification as it
    is called during public checkout.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        subtotal: The pre-tax cart subtotal.
        country: Two-letter ISO country code.
        state: Optional state/province code.
        zip_code: Optional postal/zip code.

    Returns:
        A dict with ``tax_amount`` (total tax), ``effective_rate``
        (percentage), and ``breakdown`` (list of applied rate details).
    """
    # Build conditions for geographic matching
    from sqlalchemy import or_, and_

    conditions = [
        TaxRate.store_id == store_id,
        TaxRate.is_active.is_(True),
    ]

    # Match by geographic hierarchy
    geo_conditions = [TaxRate.country == country.upper()]
    if state:
        geo_conditions.append(
            or_(
                TaxRate.state == state.upper(),
                TaxRate.state.is_(None),
            )
        )
    else:
        geo_conditions.append(TaxRate.state.is_(None))

    if zip_code:
        geo_conditions.append(
            or_(
                TaxRate.zip_code == zip_code,
                TaxRate.zip_code.is_(None),
            )
        )
    else:
        geo_conditions.append(TaxRate.zip_code.is_(None))

    conditions.extend(geo_conditions)

    result = await db.execute(
        select(TaxRate)
        .where(*conditions)
        .order_by(TaxRate.priority)
    )
    matching_rates = list(result.scalars().all())

    if not matching_rates:
        return {
            "tax_amount": Decimal("0.00"),
            "effective_rate": Decimal("0.00"),
            "breakdown": [],
        }

    # Apply tax rates in priority order
    total_tax = Decimal("0.00")
    breakdown = []

    for rate in matching_rates:
        if rate.is_inclusive:
            # Compound: apply on subtotal + accumulated tax
            taxable_amount = subtotal + total_tax
        else:
            # Non-compound: apply on original subtotal only
            taxable_amount = subtotal

        tax_contribution = taxable_amount * (rate.rate / Decimal("100"))
        tax_contribution = tax_contribution.quantize(Decimal("0.01"))
        total_tax += tax_contribution

        breakdown.append({
            "tax_rate_id": rate.id,
            "name": rate.name,
            "rate": rate.rate,
            "is_inclusive": rate.is_inclusive,
            "tax_amount": tax_contribution,
        })

    effective_rate = (
        (total_tax / subtotal * Decimal("100")) if subtotal > 0 else Decimal("0.00")
    )

    return {
        "tax_amount": total_tax,
        "effective_rate": effective_rate.quantize(Decimal("0.01")),
        "breakdown": breakdown,
    }
