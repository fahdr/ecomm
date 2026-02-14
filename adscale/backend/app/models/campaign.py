"""
Campaign model for advertising campaign management.

Represents a single advertising campaign on a connected ad platform.
Campaigns contain ad groups, which in turn contain creatives.

For Developers:
    Campaigns are the primary billable resource (max_items plan limit).
    Budget can be daily or lifetime. Status controls whether the campaign
    is actively running on the ad platform.

For QA Engineers:
    Test CRUD operations, plan limit enforcement (free: 2 campaigns),
    budget validation (daily OR lifetime, not both negative), and
    status transitions (draft -> active -> paused -> completed).

For Project Managers:
    Campaigns are the main entity users manage. Each campaign targets
    a specific objective (traffic, conversions, awareness, sales) and
    has a budget and date range.

For End Users:
    Create campaigns to promote your products. Set a daily or lifetime
    budget, choose an objective, and AdScale will optimize delivery.
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CampaignObjective(str, enum.Enum):
    """
    Campaign optimization objectives.

    Attributes:
        traffic: Drive clicks and website visits.
        conversions: Optimize for purchase or signup conversions.
        awareness: Maximize impressions and brand visibility.
        sales: Optimize for direct product sales (ROAS-focused).
    """

    traffic = "traffic"
    conversions = "conversions"
    awareness = "awareness"
    sales = "sales"


class CampaignStatus(str, enum.Enum):
    """
    Campaign lifecycle status.

    Attributes:
        draft: Campaign is being set up, not yet running.
        active: Campaign is live and delivering ads.
        paused: Campaign is temporarily stopped by the user.
        completed: Campaign has ended (past end_date or budget exhausted).
    """

    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"


class Campaign(Base):
    """
    Advertising campaign on a connected ad platform.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        ad_account_id: Foreign key to the ad account running this campaign.
        name: Human-readable campaign name.
        platform: Platform this campaign runs on (denormalized from ad_account).
        objective: Campaign optimization objective.
        budget_daily: Daily budget in USD (nullable, mutually optional with lifetime).
        budget_lifetime: Total lifetime budget in USD (nullable).
        status: Current campaign lifecycle status.
        start_date: Campaign start date (nullable for drafts).
        end_date: Campaign end date (nullable for open-ended campaigns).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        ad_account: Related AdAccount record.
        ad_groups: Ad groups within this campaign.
        metrics: Performance metrics for this campaign.
    """

    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    ad_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    objective: Mapped[CampaignObjective] = mapped_column(
        Enum(CampaignObjective), nullable=False
    )
    budget_daily: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_lifetime: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.draft, nullable=False
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    ad_account = relationship("AdAccount", back_populates="campaigns", lazy="selectin")
    ad_groups = relationship(
        "AdGroup", back_populates="campaign", lazy="selectin",
        cascade="all, delete-orphan"
    )
    metrics = relationship(
        "CampaignMetrics", back_populates="campaign", lazy="selectin",
        cascade="all, delete-orphan"
    )
