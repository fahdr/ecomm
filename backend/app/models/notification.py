"""Notification database model.

Defines the ``notifications`` table for in-app notifications delivered to
users. Notifications are triggered by system events (order placed, refund
requested, etc.) and provide a persistent feed for the dashboard.

**For Developers:**
    Import this model via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``user_id`` foreign key determines who
    receives the notification. The ``store_id`` is optional (SET NULL)
    because some notifications are platform-level (e.g. subscription
    expiring) rather than store-specific. The ``metadata`` JSON column
    stores event-specific payload data for rendering rich notification
    content.

**For QA Engineers:**
    - ``NotificationType`` enumerates all supported event types.
    - ``is_read`` starts as False and is set to True when the user views
      or dismisses the notification.
    - ``action_url`` is an optional deep-link URL that clicking the
      notification should navigate to.
    - ``metadata`` is a flexible JSON object for event-specific data
      (e.g. order total, product name, refund amount).
    - Notifications are never deleted, only marked as read.

**For End Users:**
    Notifications keep you informed about important events in your store
    -- new orders, shipment updates, refund requests, reviews, and more.
    You can see unread notifications in your dashboard bell icon and click
    them to jump directly to the relevant page.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class NotificationType(str, enum.Enum):
    """Types of in-app notifications.

    Attributes:
        order_placed: A new order was placed in the store.
        order_shipped: An order was marked as shipped.
        order_delivered: An order was marked as delivered.
        refund_requested: A customer submitted a refund request.
        refund_completed: A refund was processed and completed.
        review_received: A new product review was submitted.
        low_stock: A product variant's inventory is running low.
        subscription_expiring: The user's platform subscription is about
            to expire.
        team_invite: The user received a team invitation.
        system: A generic system-level notification.
    """

    order_placed = "order_placed"
    order_shipped = "order_shipped"
    order_delivered = "order_delivered"
    refund_requested = "refund_requested"
    refund_completed = "refund_completed"
    review_received = "review_received"
    low_stock = "low_stock"
    subscription_expiring = "subscription_expiring"
    team_invite = "team_invite"
    system = "system"


class Notification(Base):
    """SQLAlchemy model representing an in-app notification.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        user_id: Foreign key to the user who receives this notification.
        store_id: Optional foreign key to the related store (null for
            platform-level notifications).
        notification_type: The type of event that triggered this notification.
        title: Short headline of the notification.
        message: Full notification message body.
        is_read: Whether the user has viewed this notification.
        action_url: Optional URL to navigate to when the notification is
            clicked.
        metadata_: Optional JSON object with event-specific data for
            rendering.
        created_at: Timestamp when the notification was created (DB server
            time).
        user: Relationship to the User.
        store: Relationship to the Store (nullable).
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", backref="notifications", lazy="selectin")
    store = relationship("Store", backref="notifications", lazy="selectin")
