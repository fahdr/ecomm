"""Service integration database model.

Defines the ``service_integrations`` table that tracks connections between
platform users and external SaaS microservices (TrendScout, ContentForge,
etc.). Each integration represents a provisioned account in one service.

**For Developers:**
    Import via ``app.models`` for Alembic discovery. The ``ServiceName``
    and ``ServiceTier`` enums are also used by the schemas layer
    (``app.schemas.services``) for request/response validation.

**For QA Engineers:**
    - ``ServiceName`` has exactly 8 values matching the microservice names.
    - ``ServiceTier`` has 4 levels: free, starter, growth, pro.
    - A user can have at most one integration per service (unique constraint).
    - ``service_user_id`` is the user's ID within the external service.
    - ``api_key`` stores the provisioned API key for platform-to-service calls.

**For Project Managers:**
    This model supports the platform integration feature where users can
    connect to standalone AI tools directly from the dropshipping dashboard.
    Bundle pricing ties platform subscription tiers to included services.

**For End Users:**
    When you connect an AI tool from the dashboard, this record tracks
    your account in that tool, your current plan, and usage data.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ServiceName(str, enum.Enum):
    """Identifiers for the 8 standalone SaaS microservices.

    Each value corresponds to a service directory under ``services/``
    and maps to a specific automation feature (A1-A8).

    Attributes:
        trendscout: A1 -- AI-Powered Product Research.
        contentforge: A2 -- AI Product Content Generator.
        rankpilot: A3 -- Automated SEO Engine.
        flowsend: A4 -- Smart Email Marketing.
        spydrop: A5 -- Competitor Intelligence.
        postpilot: A6 -- Social Media Automation.
        adscale: A7 -- AI Ad Campaign Manager.
        shopchat: A8 -- AI Shopping Assistant.
    """

    trendscout = "trendscout"
    contentforge = "contentforge"
    rankpilot = "rankpilot"
    flowsend = "flowsend"
    spydrop = "spydrop"
    postpilot = "postpilot"
    adscale = "adscale"
    shopchat = "shopchat"


class ServiceTier(str, enum.Enum):
    """Pricing tiers available within each microservice.

    These mirror the per-service billing plans. The platform may include
    certain tiers as part of bundle pricing.

    Attributes:
        free: Free tier with basic usage limits.
        starter: Entry-level paid tier.
        growth: Mid-level tier for scaling businesses.
        pro: Highest tier with unlimited or maximum limits.
    """

    free = "free"
    starter = "starter"
    growth = "growth"
    pro = "pro"


class ServiceIntegration(Base):
    """SQLAlchemy model tracking a user's provisioned account in a microservice.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the ``users`` table.
        service_name: Which microservice this integration connects to.
        service_user_id: The user's ID within the external service.
        api_key: Encrypted API key for platform-to-service calls.
        tier: The user's current pricing tier in the service.
        is_active: Whether the integration is currently active.
        store_id: Optional foreign key linking to a specific store.
        provisioned_at: When the user was provisioned in the service.
        created_at: Record creation timestamp.
        updated_at: Record last-update timestamp.
    """

    __tablename__ = "service_integrations"
    __table_args__ = (
        UniqueConstraint("user_id", "service_name", name="uq_user_service"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_name: Mapped[ServiceName] = mapped_column(
        Enum(ServiceName, name="servicename", create_type=False),
        nullable=False,
    )
    service_user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="User ID in the external service"
    )
    api_key: Mapped[str] = mapped_column(
        Text, nullable=False, doc="API key for platform-to-service auth"
    )
    tier: Mapped[ServiceTier] = mapped_column(
        Enum(ServiceTier, name="servicetier", create_type=False),
        nullable=False,
        default=ServiceTier.free,
    )
    is_active: Mapped[bool] = mapped_column(
        default=True, nullable=False
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provisioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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

    owner = relationship("User", backref="service_integrations", lazy="selectin")
    store = relationship("Store", backref="service_integrations", lazy="selectin")
