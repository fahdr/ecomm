"""A/B testing business logic.

Handles creation, management, and variant assignment for A/B tests.
Supports split testing with multiple variants, deterministic visitor
assignment, and conversion/revenue tracking.

**For Developers:**
    Variant assignment uses a deterministic hash of the visitor ID and
    test ID so the same visitor always sees the same variant. Weights
    control traffic allocation. Status transitions follow the lifecycle:
    ``draft`` -> ``running`` -> ``paused`` | ``completed``. The
    ``record_event`` function increments counters atomically.

**For QA Engineers:**
    - ``create_test`` requires at least two variants.
    - ``get_assigned_variant`` produces deterministic assignments using
      a hash-based algorithm.
    - ``record_event`` supports ``impression`` and ``conversion`` event
      types and optional revenue tracking.
    - Status transitions are validated: cannot go from ``completed`` back
      to ``running``.
    - ``delete_test`` is only allowed for ``draft`` tests.

**For Project Managers:**
    This service powers Feature 29 (A/B Testing) from the backlog. It
    enables store owners to run experiments on their storefront (e.g.
    test different product titles, prices, or layouts) and measure
    which variant performs better.

**For End Users:**
    Run experiments on your store to find what converts best. Create
    tests with multiple variants, track impressions and conversions,
    and let data guide your decisions.
"""

import hashlib
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store, StoreStatus


# ---------------------------------------------------------------------------
# A/B test models -- import conditionally.
# ---------------------------------------------------------------------------
try:
    from app.models.ab_test import ABTest, ABTestVariant
except ImportError:
    ABTest = None  # type: ignore[assignment,misc]
    ABTestVariant = None  # type: ignore[assignment,misc]


# Valid status transitions
_VALID_TRANSITIONS = {
    "draft": {"running"},
    "running": {"paused", "completed"},
    "paused": {"running", "completed"},
    "completed": set(),  # Terminal state
}


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


async def create_test(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    description: str | None = None,
    metric: str = "conversion_rate",
    variants: list[dict] | None = None,
) -> "ABTest":
    """Create a new A/B test with variants.

    Requires at least two variants. Each variant dict should contain
    ``name`` and optionally ``weight`` (traffic allocation, defaults
    to equal distribution).

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        name: Name of the test (e.g. "Product Title Test").
        description: Optional description of the hypothesis.
        metric: The primary metric to optimise (e.g. ``"conversion_rate"``,
            ``"revenue"``, ``"click_through_rate"``).
        variants: List of variant dicts with at least ``name`` and
            optionally ``weight``, ``config`` (JSON).

    Returns:
        The newly created ABTest ORM instance with variants.

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            or fewer than two variants are provided.
    """
    await _verify_store_ownership(db, store_id, user_id)

    if not variants or len(variants) < 2:
        raise ValueError("At least two variants are required for an A/B test")

    test = ABTest(
        store_id=store_id,
        name=name,
        description=description,
        metric=metric,
        status="draft",
    )
    db.add(test)
    await db.flush()

    # Calculate default weights if not provided
    default_weight = 100 // len(variants)

    for i, v in enumerate(variants):
        variant = ABTestVariant(
            test_id=test.id,
            name=v["name"],
            weight=v.get("weight", default_weight),
            description=v.get("description"),
            is_control=v.get("is_control", i == 0),
            impressions=0,
            conversions=0,
            revenue=Decimal("0.00"),
        )
        db.add(variant)

    await db.flush()
    await db.refresh(test)
    return test


async def list_tests(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list, int]:
    """List A/B tests for a store with pagination.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (tests list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    query = select(ABTest).where(ABTest.store_id == store_id)
    count_query = select(func.count(ABTest.id)).where(ABTest.store_id == store_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(ABTest.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    tests = list(result.scalars().all())

    return tests, total


async def get_test(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    test_id: uuid.UUID,
) -> "ABTest":
    """Retrieve a single A/B test with variants.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        test_id: The UUID of the test to retrieve.

    Returns:
        The ABTest ORM instance with variants loaded.

    Raises:
        ValueError: If the store or test doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(ABTest).where(
            ABTest.id == test_id,
            ABTest.store_id == store_id,
        )
    )
    test = result.scalar_one_or_none()
    if test is None:
        raise ValueError("A/B test not found")
    return test


async def update_test(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    test_id: uuid.UUID,
    **kwargs,
) -> "ABTest":
    """Update an A/B test's fields with status transition validation.

    Validates status transitions: ``draft`` -> ``running``, ``running``
    -> ``paused``/``completed``, ``paused`` -> ``running``/``completed``.
    ``completed`` is a terminal state.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        test_id: The UUID of the test to update.
        **kwargs: Keyword arguments for fields to update (name,
            description, metric, status).

    Returns:
        The updated ABTest ORM instance.

    Raises:
        ValueError: If the store or test doesn't exist, the store belongs
            to another user, or the status transition is invalid.
    """
    test = await get_test(db, store_id, user_id, test_id)

    new_status = kwargs.get("status")
    if new_status is not None and new_status != test.status:
        valid_targets = _VALID_TRANSITIONS.get(test.status, set())
        if new_status not in valid_targets:
            raise ValueError(
                f"Cannot transition from '{test.status}' to '{new_status}'. "
                f"Valid transitions: {valid_targets or 'none (terminal state)'}"
            )

    for key, value in kwargs.items():
        if value is not None:
            setattr(test, key, value)

    await db.flush()
    await db.refresh(test)
    return test


async def delete_test(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    test_id: uuid.UUID,
) -> None:
    """Delete an A/B test (only allowed for draft tests).

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        test_id: The UUID of the test to delete.

    Raises:
        ValueError: If the store or test doesn't exist, the store belongs
            to another user, or the test is not in draft status.
    """
    test = await get_test(db, store_id, user_id, test_id)

    if test.status != "draft":
        raise ValueError(
            f"Cannot delete a test with status '{test.status}'. "
            f"Only draft tests can be deleted."
        )

    await db.delete(test)
    await db.flush()


async def record_event(
    db: AsyncSession,
    variant_id: uuid.UUID,
    event_type: str,
    revenue: Decimal | None = None,
) -> None:
    """Record an event (impression or conversion) for a test variant.

    Increments the appropriate counter on the variant record. For
    conversion events, optionally adds revenue.

    Args:
        db: Async database session.
        variant_id: The UUID of the variant to record against.
        event_type: Either ``"impression"`` or ``"conversion"``.
        revenue: Optional revenue amount for conversion events.

    Raises:
        ValueError: If the variant doesn't exist or the event type is
            invalid.
    """
    if event_type not in ("impression", "conversion"):
        raise ValueError(
            f"Invalid event type: '{event_type}'. "
            f"Must be 'impression' or 'conversion'."
        )

    result = await db.execute(
        select(ABTestVariant).where(ABTestVariant.id == variant_id)
    )
    variant = result.scalar_one_or_none()
    if variant is None:
        raise ValueError("Variant not found")

    # Verify the parent test is currently running
    test_result = await db.execute(
        select(ABTest).where(ABTest.id == variant.test_id)
    )
    test = test_result.scalar_one_or_none()
    if test is None or test.status != "running":
        raise ValueError("Test is not running — cannot record events")

    if event_type == "impression":
        variant.impressions += 1
    elif event_type == "conversion":
        variant.conversions += 1
        if revenue is not None:
            variant.revenue += revenue

    await db.flush()


async def get_assigned_variant(
    db: AsyncSession,
    test_id: uuid.UUID,
    visitor_id: str,
) -> "ABTestVariant":
    """Assign a visitor to a test variant deterministically.

    Uses a hash of the visitor ID and test ID to produce a consistent
    assignment. The same visitor always sees the same variant. Variants
    are selected according to their weight distribution.

    Args:
        db: Async database session.
        test_id: The UUID of the A/B test.
        visitor_id: A unique identifier for the visitor (e.g. session ID,
            cookie, or fingerprint).

    Returns:
        The assigned ABTestVariant ORM instance.

    Raises:
        ValueError: If the test doesn't exist or has no variants.
    """
    result = await db.execute(
        select(ABTestVariant)
        .where(ABTestVariant.test_id == test_id)
        .order_by(ABTestVariant.created_at)
    )
    variants = list(result.scalars().all())

    if not variants:
        raise ValueError("No variants found for this test")

    # Deterministic hash-based assignment
    hash_input = f"{test_id}:{visitor_id}"
    hash_value = int(
        hashlib.sha256(hash_input.encode("utf-8")).hexdigest(), 16
    )

    # Calculate total weight and find the assigned variant
    total_weight = sum(v.weight for v in variants)
    if total_weight <= 0:
        # Fallback to equal distribution
        index = hash_value % len(variants)
        return variants[index]

    bucket = hash_value % total_weight
    cumulative = 0

    for variant in variants:
        cumulative += variant.weight
        if bucket < cumulative:
            return variant

    # Fallback (should not reach here)
    return variants[-1]
