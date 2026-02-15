"""
Subscription model for Stripe billing integration.

Tracks the user's subscription state synced from Stripe webhooks.

For Developers:
    Subscription records are upserted via webhook events. The `status` field
    mirrors Stripe's subscription status. When status changes, the parent
    User's `plan` field is also updated (denormalized).

For QA Engineers:
    Test subscription lifecycle: create checkout -> webhook -> subscription active.
    In mock mode (empty STRIPE_SECRET_KEY), subscriptions are created directly.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ecomm_core.models.base import Base
from ecomm_core.models.user import PlanTier


class SubscriptionStatus(str, enum.Enum):
    """
    Subscription status values mirroring Stripe's subscription statuses.

    Attributes:
        active: Subscription is paid and active.
        trialing: Subscription is in free trial period.
        past_due: Payment failed, grace period active.
        canceled: Subscription has been canceled.
        unpaid: Payment has failed beyond grace period.
        incomplete: Initial payment not yet completed.
    """

    active = "active"
    trialing = "trialing"
    past_due = "past_due"
    canceled = "canceled"
    unpaid = "unpaid"
    incomplete = "incomplete"


class Subscription(Base):
    """
    Stripe subscription record for a user.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        stripe_subscription_id: Stripe's subscription ID.
        stripe_price_id: Stripe Price ID for the subscribed plan.
        plan: The plan tier this subscription grants.
        status: Current subscription status from Stripe.
        current_period_start: Start of the current billing period.
        current_period_end: End of the current billing period.
        cancel_at_period_end: Whether cancellation is scheduled.
        trial_start: Trial period start (if applicable).
        trial_end: Trial period end (if applicable).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Related User record.
    """

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    stripe_subscription_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    stripe_price_id: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[PlanTier] = mapped_column(Enum(PlanTier), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), nullable=False
    )
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    trial_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", back_populates="subscription", lazy="selectin")
