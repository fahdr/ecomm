"""
Campaign Metrics model for tracking ad performance data.

Stores daily performance metrics for each campaign, including impressions,
clicks, conversions, spend, and revenue. Computed fields (ROAS, CPA, CTR)
are derived from these base metrics.

For Developers:
    Metrics are synced daily from the ad platform via Celery tasks.
    The `roas`, `cpa`, and `ctr` fields are pre-computed during sync
    for fast dashboard queries. Use the metrics_service for aggregation.

For QA Engineers:
    Test metric creation, aggregation (sum over date ranges), computed
    field accuracy (ROAS = revenue/spend, CPA = spend/conversions,
    CTR = clicks/impressions * 100).

For Project Managers:
    Campaign metrics drive the analytics dashboard. Users can see
    daily performance trends, compare campaigns, and identify
    optimization opportunities.

For End Users:
    View your campaign performance in the Analytics section.
    Track spend, revenue, ROAS, and other key metrics over time.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CampaignMetrics(Base):
    """
    Daily performance metrics for a campaign.

    Attributes:
        id: Unique identifier (UUID v4).
        campaign_id: Foreign key to the campaign.
        date: The date these metrics apply to.
        impressions: Number of times the ad was shown.
        clicks: Number of clicks on the ad.
        conversions: Number of completed conversion actions.
        spend: Total ad spend in USD for this day.
        revenue: Total revenue attributed to ads for this day.
        roas: Return on ad spend (revenue / spend, nullable if no spend).
        cpa: Cost per acquisition (spend / conversions, nullable if no conversions).
        ctr: Click-through rate percentage (clicks / impressions * 100, nullable).
        created_at: Record creation timestamp.
        campaign: Related Campaign record.
    """

    __tablename__ = "campaign_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    spend: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    roas: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="metrics", lazy="selectin")
