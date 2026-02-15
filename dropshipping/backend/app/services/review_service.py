"""Review business logic.

Handles product review submission, moderation, and public retrieval for
storefront display. Reviews support a moderation workflow where store
owners approve or reject submissions before they appear publicly.

**For Developers:**
    ``create_review`` automatically checks if the customer has purchased
    the product to set the ``is_verified_purchase`` flag. Rating
    aggregation (average and count) is denormalised onto the Product
    model via ``_update_product_rating_stats`` for performance.

**For QA Engineers:**
    - ``create_review`` checks for verified purchase by querying paid
      orders containing the product for the given customer email.
    - ``update_review_status`` recalculates the product's average rating
      whenever a review is approved or rejected.
    - ``get_public_reviews`` returns only approved reviews, sorted newest
      first.
    - ``get_review_stats`` computes rating distribution (count per star
      level) for a product.

**For Project Managers:**
    This service powers Feature 12 (Product Reviews) from the backlog.
    It provides social proof on product pages and enables store owners
    to moderate user-generated content.

**For End Users:**
    Customers can leave ratings and written reviews on products they've
    purchased. Store owners moderate reviews before they appear on the
    storefront. Verified purchase badges indicate the reviewer actually
    bought the product.
"""

import uuid

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.review import Review, ReviewStatus
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


async def _check_verified_purchase(
    db: AsyncSession,
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    customer_email: str,
) -> bool:
    """Check if a customer has a paid order containing the given product.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        product_id: The product's UUID.
        customer_email: The customer's email address.

    Returns:
        True if the customer has a confirmed (paid, shipped, or delivered)
        order containing the product, False otherwise.
    """
    result = await db.execute(
        select(func.count(OrderItem.id))
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            Order.store_id == store_id,
            Order.customer_email == customer_email,
            Order.status.in_([
                OrderStatus.paid,
                OrderStatus.shipped,
                OrderStatus.delivered,
            ]),
            OrderItem.product_id == product_id,
        )
    )
    count = result.scalar_one()
    return count > 0


async def _update_product_rating_stats(
    db: AsyncSession,
    product_id: uuid.UUID,
) -> None:
    """Recalculate and update the denormalised rating stats on a Product.

    Computes the average rating and review count from all approved
    reviews and writes them to the product record. If the Product model
    does not have ``avg_rating`` or ``review_count`` columns yet, this
    function silently returns without error.

    Args:
        db: Async database session.
        product_id: The UUID of the product to update.
    """
    result = await db.execute(
        select(
            func.avg(Review.rating),
            func.count(Review.id),
        ).where(
            Review.product_id == product_id,
            Review.status == ReviewStatus.approved,
        )
    )
    row = result.one()
    avg_rating = float(row[0]) if row[0] is not None else 0.0
    review_count = row[1]

    product_result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = product_result.scalar_one_or_none()
    if product is not None:
        # Update denormalised fields if they exist on the model
        if hasattr(product, "avg_rating"):
            product.avg_rating = round(avg_rating, 2)
        if hasattr(product, "review_count"):
            product.review_count = review_count
        await db.flush()


async def create_review(
    db: AsyncSession,
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    customer_id: uuid.UUID | None,
    customer_name: str,
    customer_email: str,
    rating: int,
    title: str | None = None,
    body: str | None = None,
) -> Review:
    """Submit a new product review.

    Automatically determines whether the reviewer has a verified purchase
    of the product. The review starts in ``pending`` status and must be
    approved by the store owner before appearing publicly.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        product_id: The UUID of the product being reviewed.
        customer_id: Optional UUID of the customer's user account.
        customer_name: Display name of the reviewer.
        customer_email: Email of the reviewer.
        rating: Star rating from 1 to 5.
        title: Optional short summary of the review.
        body: Optional detailed review text.

    Returns:
        The newly created Review ORM instance.

    Raises:
        ValueError: If the rating is outside the 1-5 range or the
            product doesn't exist in the store.
    """
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5")

    # Verify product exists in the store
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.store_id == store_id,
        )
    )
    if product_result.scalar_one_or_none() is None:
        raise ValueError("Product not found in this store")

    # Check for verified purchase
    is_verified = await _check_verified_purchase(
        db, store_id, product_id, customer_email
    )

    review = Review(
        store_id=store_id,
        product_id=product_id,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_email=customer_email,
        rating=rating,
        title=title,
        body=body,
        status=ReviewStatus.pending,
        is_verified_purchase=is_verified,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)
    return review


async def list_reviews(
    db: AsyncSession,
    store_id: uuid.UUID,
    product_id: uuid.UUID | None = None,
    status_filter: ReviewStatus | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Review], int]:
    """List reviews for a store with optional product and status filtering.

    Used by store owners in the admin dashboard to moderate reviews.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        product_id: Optional product UUID to filter by.
        status_filter: Optional moderation status to filter by.
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (reviews list, total count).
    """
    query = select(Review).where(Review.store_id == store_id)
    count_query = select(func.count(Review.id)).where(Review.store_id == store_id)

    if product_id is not None:
        query = query.where(Review.product_id == product_id)
        count_query = count_query.where(Review.product_id == product_id)

    if status_filter is not None:
        query = query.where(Review.status == status_filter)
        count_query = count_query.where(Review.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Review.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    reviews = list(result.scalars().all())

    return reviews, total


async def get_review(
    db: AsyncSession,
    review_id: uuid.UUID,
) -> Review:
    """Retrieve a single review by ID.

    Args:
        db: Async database session.
        review_id: The UUID of the review to retrieve.

    Returns:
        The Review ORM instance.

    Raises:
        ValueError: If the review doesn't exist.
    """
    result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise ValueError("Review not found")
    return review


async def update_review_status(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    review_id: uuid.UUID,
    status: ReviewStatus,
) -> Review:
    """Update a review's moderation status.

    Recalculates the product's denormalised average rating and review
    count after the status change takes effect.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        review_id: The UUID of the review to update.
        status: The new moderation status (pending, approved, rejected).

    Returns:
        The updated Review ORM instance.

    Raises:
        ValueError: If the store or review doesn't exist, or the store
            belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    review = await get_review(db, review_id)
    if review.store_id != store_id:
        raise ValueError("Review not found in this store")

    review.status = status
    await db.flush()

    # Recalculate denormalised rating stats
    await _update_product_rating_stats(db, review.product_id)

    await db.refresh(review)
    return review


async def get_review_stats(
    db: AsyncSession,
    store_id: uuid.UUID,
    product_id: uuid.UUID,
) -> dict:
    """Get review statistics for a product.

    Computes the average rating, total approved review count, and a
    rating distribution (count of reviews per star level 1-5).

    Args:
        db: Async database session.
        store_id: The store's UUID.
        product_id: The UUID of the product.

    Returns:
        A dict with ``average_rating`` (float), ``total_reviews`` (int),
        and ``rating_distribution`` (dict mapping star levels 1-5 to counts).
    """
    # Overall stats
    stats_result = await db.execute(
        select(
            func.avg(Review.rating),
            func.count(Review.id),
        ).where(
            Review.store_id == store_id,
            Review.product_id == product_id,
            Review.status == ReviewStatus.approved,
        )
    )
    stats_row = stats_result.one()
    avg_rating = float(stats_row[0]) if stats_row[0] is not None else 0.0
    total_reviews = stats_row[1]

    # Rating distribution
    distribution_result = await db.execute(
        select(
            Review.rating,
            func.count(Review.id),
        ).where(
            Review.store_id == store_id,
            Review.product_id == product_id,
            Review.status == ReviewStatus.approved,
        ).group_by(Review.rating)
    )
    distribution = {i: 0 for i in range(1, 6)}
    for row in distribution_result.fetchall():
        distribution[row[0]] = row[1]

    return {
        "average_rating": round(avg_rating, 2),
        "total_reviews": total_reviews,
        "rating_distribution": distribution,
    }


async def get_public_reviews(
    db: AsyncSession,
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Review], int]:
    """Get approved reviews for a product on the public storefront.

    Only returns reviews with ``approved`` status, sorted by newest
    first. Does not require store ownership verification.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        product_id: The UUID of the product.
        page: Page number (1-based).
        per_page: Number of items per page.

    Returns:
        A tuple of (reviews list, total count).
    """
    query = select(Review).where(
        Review.store_id == store_id,
        Review.product_id == product_id,
        Review.status == ReviewStatus.approved,
    )
    count_query = select(func.count(Review.id)).where(
        Review.store_id == store_id,
        Review.product_id == product_id,
        Review.status == ReviewStatus.approved,
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Review.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    reviews = list(result.scalars().all())

    return reviews, total
