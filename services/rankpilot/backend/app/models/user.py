"""
User model for the RankPilot service.

Each service maintains its own independent user table. Users can sign up
directly on the service or be provisioned via the dropshipping platform API.

For Developers:
    The `plan` field is denormalized from the Subscription model for fast
    lookups. It's updated whenever the subscription changes.
    `external_platform_id` and `external_store_id` are set when a user is
    provisioned from the dropshipping platform.

For QA Engineers:
    Test user creation via POST /api/v1/auth/register.
    Verify plan enforcement by checking resource limits per tier.

For End Users:
    Your account stores your email, subscription plan, and API access.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PlanTier(str, enum.Enum):
    """
    Subscription plan tiers available for this service.

    Attributes:
        free: Free tier with limited usage.
        pro: Professional tier with expanded limits.
        enterprise: Enterprise tier with unlimited usage and API access.
    """

    free = "free"
    pro = "pro"
    enterprise = "enterprise"


class User(Base):
    """
    User account for the RankPilot service.

    Attributes:
        id: Unique identifier (UUID v4).
        email: User's email address (unique, used for login).
        hashed_password: Bcrypt-hashed password.
        is_active: Whether the account is active (can be suspended).
        plan: Current subscription tier (denormalized from Subscription).
        stripe_customer_id: Stripe Customer ID for billing.
        external_platform_id: Dropshipping platform user ID (if provisioned via API).
        external_store_id: Dropshipping platform store ID (if linked to a store).
        created_at: Account creation timestamp.
        updated_at: Last modification timestamp.
        subscription: Related Subscription record.
        api_keys: Related API keys for programmatic access.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    plan: Mapped[PlanTier] = mapped_column(
        Enum(PlanTier), default=PlanTier.free, nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    external_platform_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    external_store_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    subscription = relationship(
        "Subscription", back_populates="owner", uselist=False, lazy="selectin"
    )
    api_keys = relationship("ApiKey", back_populates="owner", lazy="selectin")
