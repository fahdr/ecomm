"""Notification business logic.

Handles in-app notification creation, listing, read status management,
and cleanup. Notifications are scoped to individual users and can be
associated with a store for context.

**For Developers:**
    Notifications are user-scoped (not store-scoped) so a user sees all
    notifications across their stores in one feed. The ``create_notification``
    function is called internally by other services (e.g. order service,
    refund service) to notify the user of important events. The
    ``action_url`` field provides a deep link to the relevant dashboard
    page. The ``metadata`` field stores arbitrary JSON for rich
    notification rendering.

**For QA Engineers:**
    - ``list_notifications`` supports ``unread_only`` filtering and
      pagination.
    - ``mark_as_read`` accepts a list of notification IDs for batch
      marking.
    - ``mark_all_as_read`` marks all unread notifications for the user.
    - ``get_unread_count`` returns a scalar count for badge display.
    - ``delete_notification`` is a hard delete.

**For Project Managers:**
    This service powers Feature 25 (Notifications) from the backlog.
    It provides a notification bell/feed in the dashboard for real-time
    awareness of store events.

**For End Users:**
    Receive in-app notifications when important events happen in your
    store, like new orders, refund requests, or low stock alerts. Mark
    them as read or dismiss them from your notification feed.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Notification model -- import conditionally.
# ---------------------------------------------------------------------------
try:
    from app.models.notification import Notification
except ImportError:
    Notification = None  # type: ignore[assignment,misc]


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    store_id: uuid.UUID | None,
    notification_type: str,
    title: str,
    message: str,
    action_url: str | None = None,
    metadata: dict | None = None,
) -> "Notification":
    """Create a new notification for a user.

    Typically called internally by other services to notify the user
    of events like new orders, reviews, or system alerts.

    Args:
        db: Async database session.
        user_id: The UUID of the user to notify.
        store_id: Optional UUID of the related store for context.
        notification_type: The event type string (e.g. ``"order.created"``,
            ``"review.pending"``, ``"system.alert"``).
        title: Short notification title (e.g. "New Order Received").
        message: Notification body text with details.
        action_url: Optional deep link URL to the relevant dashboard page.
        metadata: Optional JSON metadata for rich rendering.

    Returns:
        The newly created Notification ORM instance.
    """
    notification = Notification(
        user_id=user_id,
        store_id=store_id,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
        metadata=metadata or {},
        is_read=False,
    )
    db.add(notification)
    await db.flush()
    await db.refresh(notification)
    return notification


async def list_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    unread_only: bool = False,
) -> tuple[list, int]:
    """List notifications for a user with pagination.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        page: Page number (1-based).
        per_page: Number of items per page.
        unread_only: If True, only return unread notifications.

    Returns:
        A tuple of (notifications list, total count).
    """
    query = select(Notification).where(Notification.user_id == user_id)
    count_query = select(func.count(Notification.id)).where(
        Notification.user_id == user_id
    )

    if unread_only:
        query = query.where(Notification.is_read.is_(False))
        count_query = count_query.where(Notification.is_read.is_(False))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    notifications = list(result.scalars().all())

    return notifications, total


async def mark_as_read(
    db: AsyncSession,
    user_id: uuid.UUID,
    notification_ids: list[uuid.UUID],
) -> int:
    """Mark specific notifications as read.

    Only updates notifications belonging to the given user.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        notification_ids: List of notification UUIDs to mark as read.

    Returns:
        The number of notifications updated.
    """
    if not notification_ids:
        return 0

    result = await db.execute(
        update(Notification)
        .where(
            Notification.id.in_(notification_ids),
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.flush()
    return result.rowcount


async def mark_all_as_read(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    """Mark all unread notifications as read for a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        The number of notifications updated.
    """
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.flush()
    return result.rowcount


async def get_unread_count(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    """Get the count of unread notifications for a user.

    Used for displaying a notification badge count in the UI.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        The number of unread notifications.
    """
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    return result.scalar_one()


async def delete_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> None:
    """Permanently delete a notification.

    Only deletes the notification if it belongs to the given user.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        notification_id: The UUID of the notification to delete.

    Raises:
        ValueError: If the notification doesn't exist or belongs to
            a different user.
    """
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise ValueError("Notification not found")

    await db.delete(notification)
    await db.flush()
