"""
Ad Group model for organizing ads within campaigns.

Ad groups sit between campaigns and creatives, defining targeting
parameters and bid strategies for a subset of ads.

For Developers:
    Ad groups are the secondary billable resource (max_secondary plan limit).
    The `targeting` field is a JSON dict storing audience parameters
    (age, gender, interests, locations). `bid_strategy` controls how
    the platform optimizes bids.

For QA Engineers:
    Test CRUD operations, plan limit enforcement (free: 5 ad groups),
    JSON targeting validation, and bid strategy options.

For Project Managers:
    Ad groups let users segment their audience within a campaign.
    Each ad group can have different targeting and bidding rules.

For End Users:
    Use ad groups to target different audiences within a campaign.
    Set targeting criteria like age, interests, and locations.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BidStrategy(str, enum.Enum):
    """
    Bidding strategies for ad delivery optimization.

    Attributes:
        manual: Manual CPC bidding — user sets exact bid amount.
        auto_cpc: Automatic CPC — platform optimizes cost per click.
        target_roas: Target ROAS — optimize for a specific return on ad spend.
        maximize_conversions: Maximize conversions within the budget.
    """

    manual = "manual"
    auto_cpc = "auto_cpc"
    target_roas = "target_roas"
    maximize_conversions = "maximize_conversions"


class AdGroupStatus(str, enum.Enum):
    """
    Ad group activation status.

    Attributes:
        active: Ad group is delivering ads.
        paused: Ad group is temporarily stopped.
    """

    active = "active"
    paused = "paused"


class AdGroup(Base):
    """
    Ad group within a campaign, defining targeting and bidding.

    Attributes:
        id: Unique identifier (UUID v4).
        campaign_id: Foreign key to the parent campaign.
        name: Human-readable ad group name.
        targeting: JSON dict with audience targeting parameters.
        bid_strategy: Bidding optimization strategy.
        bid_amount: Manual bid amount in USD (nullable for auto strategies).
        status: Current ad group status (active or paused).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        campaign: Related Campaign record.
        creatives: Ad creatives within this ad group.
    """

    __tablename__ = "ad_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    targeting: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    bid_strategy: Mapped[BidStrategy] = mapped_column(
        Enum(BidStrategy), default=BidStrategy.auto_cpc, nullable=False
    )
    bid_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[AdGroupStatus] = mapped_column(
        Enum(AdGroupStatus), default=AdGroupStatus.active, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="ad_groups", lazy="selectin")
    creatives = relationship(
        "AdCreative", back_populates="ad_group", lazy="selectin",
        cascade="all, delete-orphan"
    )
