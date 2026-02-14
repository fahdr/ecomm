"""
Email analytics service.

Provides aggregate analytics across campaigns and flows, including
open rates, click rates, bounce rates, and per-campaign breakdowns.

For Developers:
    - Analytics are computed from EmailEvent records in real time.
    - Rates are calculated as percentages (0-100).
    - Division by zero is handled (returns 0.0 for empty datasets).
    - Per-campaign breakdown uses denormalized counts on Campaign model.

For QA Engineers:
    Test: aggregate analytics with no data (zeros), with campaign events,
    rate calculations accuracy, per-campaign breakdown.

For Project Managers:
    Analytics drive user retention — clear performance metrics help
    email marketers optimize their campaigns.

For End Users:
    View your email performance metrics: how many emails were sent,
    opened, clicked, and bounced. Track improvement over time.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, EmailEvent
from app.models.contact import Contact
from app.models.flow import Flow
from app.schemas.email import AggregateAnalytics, CampaignAnalytics


def _safe_rate(numerator: int, denominator: int) -> float:
    """
    Calculate a percentage rate safely, avoiding division by zero.

    Args:
        numerator: The count of the subset (e.g., opens).
        denominator: The count of the whole (e.g., sent).

    Returns:
        Rate as a float percentage (0-100), rounded to 2 decimals.
    """
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


async def get_aggregate_analytics(
    db: AsyncSession, user_id: uuid.UUID
) -> AggregateAnalytics:
    """
    Get aggregate email analytics for a user across all campaigns and flows.

    Computes totals and rates from EmailEvent records and Campaign/Flow/Contact
    counts.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        AggregateAnalytics with totals, rates, and per-campaign breakdown.
    """
    # Count contacts
    contact_count_result = await db.execute(
        select(func.count(Contact.id)).where(Contact.user_id == user_id)
    )
    total_contacts = contact_count_result.scalar() or 0

    # Count campaigns
    campaign_count_result = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.user_id == user_id)
    )
    total_campaigns = campaign_count_result.scalar() or 0

    # Count flows
    flow_count_result = await db.execute(
        select(func.count(Flow.id)).where(Flow.user_id == user_id)
    )
    total_flows = flow_count_result.scalar() or 0

    # Aggregate event counts across user's campaigns
    campaigns_result = await db.execute(
        select(Campaign).where(Campaign.user_id == user_id)
    )
    campaigns = list(campaigns_result.scalars().all())

    total_sent = sum(c.sent_count for c in campaigns)
    total_opens = sum(c.open_count for c in campaigns)
    total_clicks = sum(c.click_count for c in campaigns)
    total_bounces = sum(c.bounce_count for c in campaigns)

    # Per-campaign breakdown
    campaign_analytics = []
    for c in campaigns:
        if c.status == "sent" or c.sent_count > 0:
            campaign_analytics.append(
                CampaignAnalytics(
                    campaign_id=c.id,
                    campaign_name=c.name,
                    total_sent=c.sent_count,
                    total_opened=c.open_count,
                    total_clicked=c.click_count,
                    total_bounced=c.bounce_count,
                    open_rate=_safe_rate(c.open_count, c.sent_count),
                    click_rate=_safe_rate(c.click_count, c.sent_count),
                    bounce_rate=_safe_rate(c.bounce_count, c.sent_count),
                )
            )

    return AggregateAnalytics(
        total_emails_sent=total_sent,
        total_opens=total_opens,
        total_clicks=total_clicks,
        total_bounces=total_bounces,
        total_contacts=total_contacts,
        total_campaigns=total_campaigns,
        total_flows=total_flows,
        overall_open_rate=_safe_rate(total_opens, total_sent),
        overall_click_rate=_safe_rate(total_clicks, total_sent),
        overall_bounce_rate=_safe_rate(total_bounces, total_sent),
        campaigns=campaign_analytics,
    )


async def get_campaign_analytics(
    db: AsyncSession, user_id: uuid.UUID, campaign_id: uuid.UUID
) -> CampaignAnalytics | None:
    """
    Get analytics for a single campaign.

    Args:
        db: Async database session.
        user_id: The user's UUID (for access control).
        campaign_id: The campaign's UUID.

    Returns:
        CampaignAnalytics if found, None otherwise.
    """
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id, Campaign.user_id == user_id
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        return None

    return CampaignAnalytics(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        total_sent=campaign.sent_count,
        total_opened=campaign.open_count,
        total_clicked=campaign.click_count,
        total_bounced=campaign.bounce_count,
        open_rate=_safe_rate(campaign.open_count, campaign.sent_count),
        click_rate=_safe_rate(campaign.click_count, campaign.sent_count),
        bounce_rate=_safe_rate(campaign.bounce_count, campaign.sent_count),
    )
