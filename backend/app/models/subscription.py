"""Subscription database model.

Defines the ``subscriptions`` table that tracks Stripe subscription
state for platform billing. Each subscription belongs to a user.
A user can have at most one active subscription.

**For Developers:**
    Import via ``app.models`` for Alembic discovery.
    The ``stripe_subscription_id`` is the primary link to Stripe.
    ``status`` mirrors Stripe's subscription status enum.

**For QA Engineers:**
    - ``status`` values: active, trialing, past_due, canceled, unpaid,
      incomplete.
    - ``current_period_end`` determines when the subscription expires.
    - ``cancel_at_period_end`` means the user requested cancellation
      but the subscription remains active until the period ends.

**For End Users:**
    Your subscription determines your plan limits (stores, products,
    orders). You can manage it from the Billing page in the dashboard.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.plans import PlanTier
from app.database import Base


class SubscriptionStatus(str, enum.Enum):
    """Stripe subscription status values.

    These mirror the lifecycle states reported by Stripe webhooks.
    """

    active = "active"
    trialing = "trialing"
    past_due = "past_due"
    canceled = "canceled"
    unpaid = "unpaid"
    incomplete = "incomplete"


class Subscription(Base):
    """SQLAlchemy model tracking a user's Stripe subscription.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the ``users`` table.
        stripe_subscription_id: Stripe Subscription object ID (unique).
        stripe_price_id: Stripe Price object ID for the subscribed plan.
        plan: The plan tier this subscription grants.
        status: Current Stripe subscription status.
        current_period_start: Start of the current billing period.
        current_period_end: End of the current billing period.
        cancel_at_period_end: Whether the user has requested cancellation.
        trial_start: Start of the free trial period (if any).
        trial_end: End of the free trial period (if any).
        created_at: Timestamp when the record was created.
        updated_at: Timestamp of the last update.
    """

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stripe_subscription_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    stripe_price_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    plan: Mapped[PlanTier] = mapped_column(
        Enum(PlanTier, name="plantier", create_type=False),
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscriptionstatus"),
        nullable=False,
    )
    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    trial_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", backref="subscription", lazy="selectin")
