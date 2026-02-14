"""Segment business logic.

Handles CRUD operations for customer segments, which group customers
based on shared characteristics or manual assignment. Segments are
used for targeted marketing, email campaigns, and analytics.

**For Developers:**
    Segments support two types: ``manual`` (customers are explicitly
    added/removed) and ``dynamic`` (customers match a set of rules,
    though rule evaluation is not yet implemented). The ``rules``
    field stores a JSON structure defining filter criteria for dynamic
    segments. The ``segment_customers`` junction table links customers
    to manual segments.

**For QA Engineers:**
    - ``create_segment`` validates that the name is not empty.
    - ``add_customers_to_segment`` is idempotent (skips duplicates).
    - ``get_segment_customers`` paginates the customer list.
    - ``delete_segment`` is a hard delete with cascade on junction records.

**For Project Managers:**
    This service powers Feature 19 (Customer Segments) from the backlog.
    It enables store owners to group customers for targeted communications
    and analysis.

**For End Users:**
    Create customer segments to group buyers by shared traits (e.g.
    "VIP Customers", "Repeat Buyers"). Use segments to target email
    campaigns and track customer cohort performance.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store, StoreStatus


# ---------------------------------------------------------------------------
# Segment models -- import conditionally as models may be created by
# another agent.
# ---------------------------------------------------------------------------
try:
    from app.models.segment import Segment, SegmentCustomer
except ImportError:
    Segment = None  # type: ignore[assignment,misc]
    SegmentCustomer = None  # type: ignore[assignment,misc]


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


async def create_segment(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    description: str | None = None,
    segment_type: str = "manual",
    rules: dict | None = None,
) -> "Segment":
    """Create a new customer segment for a store.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        name: Display name of the segment.
        description: Optional description of the segment's purpose.
        segment_type: Type of segment: ``"manual"`` or ``"dynamic"``.
        rules: Optional JSON rules for dynamic segment filtering.

    Returns:
        The newly created Segment ORM instance.

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            or the name is empty.
    """
    await _verify_store_ownership(db, store_id, user_id)

    if not name or not name.strip():
        raise ValueError("Segment name cannot be empty")

    segment = Segment(
        store_id=store_id,
        name=name.strip(),
        description=description,
        segment_type=segment_type,
        rules=rules or {},
    )
    db.add(segment)
    await db.flush()
    await db.refresh(segment)
    return segment


async def list_segments(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list, int]:
    """List customer segments for a store with pagination.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (segments list, total count).

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    query = select(Segment).where(Segment.store_id == store_id)
    count_query = select(func.count(Segment.id)).where(Segment.store_id == store_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Segment.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    segments = list(result.scalars().all())

    return segments, total


async def get_segment(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    segment_id: uuid.UUID,
) -> "Segment":
    """Retrieve a single segment, verifying store ownership.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        segment_id: The UUID of the segment to retrieve.

    Returns:
        The Segment ORM instance.

    Raises:
        ValueError: If the store or segment doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(Segment).where(
            Segment.id == segment_id,
            Segment.store_id == store_id,
        )
    )
    segment = result.scalar_one_or_none()
    if segment is None:
        raise ValueError("Segment not found")
    return segment


async def update_segment(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    segment_id: uuid.UUID,
    **kwargs,
) -> "Segment":
    """Update a segment's fields (partial update).

    Only provided (non-None) keyword arguments are applied.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        segment_id: The UUID of the segment to update.
        **kwargs: Keyword arguments for fields to update (name,
            description, segment_type, rules).

    Returns:
        The updated Segment ORM instance.

    Raises:
        ValueError: If the store or segment doesn't exist, or the store
            belongs to another user.
    """
    segment = await get_segment(db, store_id, user_id, segment_id)

    for key, value in kwargs.items():
        if value is not None:
            setattr(segment, key, value)

    await db.flush()
    await db.refresh(segment)
    return segment


async def delete_segment(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    segment_id: uuid.UUID,
) -> None:
    """Permanently delete a segment and its customer associations.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        segment_id: The UUID of the segment to delete.

    Raises:
        ValueError: If the store or segment doesn't exist, or the store
            belongs to another user.
    """
    segment = await get_segment(db, store_id, user_id, segment_id)
    await db.delete(segment)
    await db.flush()


async def add_customers_to_segment(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    segment_id: uuid.UUID,
    customer_ids: list[uuid.UUID],
) -> int:
    """Add customers to a segment.

    Idempotent: customers already in the segment are silently skipped.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        segment_id: The UUID of the segment.
        customer_ids: List of customer (user) UUIDs to add.

    Returns:
        The number of customers newly added (excludes duplicates).

    Raises:
        ValueError: If the store or segment doesn't exist, or the store
            belongs to another user.
    """
    await get_segment(db, store_id, user_id, segment_id)

    added_count = 0
    for customer_id in customer_ids:
        existing = await db.execute(
            select(SegmentCustomer).where(
                SegmentCustomer.segment_id == segment_id,
                SegmentCustomer.customer_id == customer_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(SegmentCustomer(
                segment_id=segment_id,
                customer_id=customer_id,
            ))
            added_count += 1

    await db.flush()
    return added_count


async def remove_customer_from_segment(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    segment_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> None:
    """Remove a customer from a segment.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        segment_id: The UUID of the segment.
        customer_id: The UUID of the customer to remove.

    Raises:
        ValueError: If the store or segment doesn't exist, the store
            belongs to another user, or the customer is not in the segment.
    """
    await get_segment(db, store_id, user_id, segment_id)

    result = await db.execute(
        select(SegmentCustomer).where(
            SegmentCustomer.segment_id == segment_id,
            SegmentCustomer.customer_id == customer_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise ValueError("Customer is not in this segment")

    await db.delete(link)
    await db.flush()


async def get_segment_customers(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    segment_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list, int]:
    """Get customers belonging to a segment with pagination.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        segment_id: The UUID of the segment.
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (SegmentCustomer link records, total count).

    Raises:
        ValueError: If the store or segment doesn't exist, or the store
            belongs to another user.
    """
    await get_segment(db, store_id, user_id, segment_id)

    query = select(SegmentCustomer).where(SegmentCustomer.segment_id == segment_id)
    count_query = select(func.count(SegmentCustomer.id)).where(
        SegmentCustomer.segment_id == segment_id
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(SegmentCustomer.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    customers = list(result.scalars().all())

    return customers, total
