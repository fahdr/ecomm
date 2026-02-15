"""
Campaign metrics aggregation service.

Provides functions to query, aggregate, and compute performance metrics
for campaigns. Calculates ROAS, CPA, CTR, and trend data.

For Developers:
    Use `get_campaign_metrics` for per-campaign daily data.
    Use `get_metrics_overview` for cross-campaign aggregation.
    Use `get_metrics_by_date_range` for filtered time-series data.

For QA Engineers:
    Test metric aggregation accuracy (sum, average calculations),
    date range filtering, empty data handling, and division-by-zero
    protection for ROAS/CPA/CTR.

For Project Managers:
    Metrics drive the analytics dashboard — accurate aggregation
    is critical for users making budget optimization decisions.

For End Users:
    View your campaign performance metrics to understand what's
    working and optimize your advertising spend.
"""

import uuid
from datetime import date

from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.campaign_metrics import CampaignMetrics


async def get_campaign_metrics(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    offset: int = 0,
    limit: int = 90,
) -> tuple[list[CampaignMetrics], int]:
    """
    Get daily metrics for a specific campaign with optional date filtering.

    Args:
        db: Async database session.
        campaign_id: UUID of the campaign.
        start_date: Filter metrics from this date (inclusive, optional).
        end_date: Filter metrics up to this date (inclusive, optional).
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 90 — ~3 months).

    Returns:
        Tuple of (list of CampaignMetrics, total count).
    """
    query = select(CampaignMetrics).where(
        CampaignMetrics.campaign_id == campaign_id
    )
    count_query = select(sql_func.count(CampaignMetrics.id)).where(
        CampaignMetrics.campaign_id == campaign_id
    )

    if start_date:
        query = query.where(CampaignMetrics.date >= start_date)
        count_query = count_query.where(CampaignMetrics.date >= start_date)
    if end_date:
        query = query.where(CampaignMetrics.date <= end_date)
        count_query = count_query.where(CampaignMetrics.date <= end_date)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(CampaignMetrics.date.desc()).offset(offset).limit(limit)
    )
    metrics = list(result.scalars().all())

    return metrics, total


async def get_metrics_overview(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """
    Get aggregated metrics overview across all user campaigns.

    Computes totals for spend, revenue, impressions, clicks, and
    conversions, plus averages for ROAS, CTR, and CPA.

    Args:
        db: Async database session.
        user_id: UUID of the user.
        start_date: Filter metrics from this date (inclusive, optional).
        end_date: Filter metrics up to this date (inclusive, optional).

    Returns:
        Dict with total_spend, total_revenue, total_impressions,
        total_clicks, total_conversions, avg_roas, avg_ctr, avg_cpa.
    """
    # Get all campaign IDs for this user
    campaign_ids_query = select(Campaign.id).where(Campaign.user_id == user_id)
    campaign_ids_result = await db.execute(campaign_ids_query)
    campaign_ids = [row[0] for row in campaign_ids_result.all()]

    if not campaign_ids:
        return {
            "total_spend": 0.0,
            "total_revenue": 0.0,
            "total_impressions": 0,
            "total_clicks": 0,
            "total_conversions": 0,
            "avg_roas": None,
            "avg_ctr": None,
            "avg_cpa": None,
        }

    # Build aggregation query
    query = select(
        sql_func.coalesce(sql_func.sum(CampaignMetrics.spend), 0.0).label("total_spend"),
        sql_func.coalesce(sql_func.sum(CampaignMetrics.revenue), 0.0).label("total_revenue"),
        sql_func.coalesce(sql_func.sum(CampaignMetrics.impressions), 0).label("total_impressions"),
        sql_func.coalesce(sql_func.sum(CampaignMetrics.clicks), 0).label("total_clicks"),
        sql_func.coalesce(sql_func.sum(CampaignMetrics.conversions), 0).label("total_conversions"),
    ).where(CampaignMetrics.campaign_id.in_(campaign_ids))

    if start_date:
        query = query.where(CampaignMetrics.date >= start_date)
    if end_date:
        query = query.where(CampaignMetrics.date <= end_date)

    result = await db.execute(query)
    row = result.one()

    total_spend = float(row.total_spend)
    total_revenue = float(row.total_revenue)
    total_impressions = int(row.total_impressions)
    total_clicks = int(row.total_clicks)
    total_conversions = int(row.total_conversions)

    # Calculate derived metrics with division-by-zero protection
    avg_roas = round(total_revenue / total_spend, 2) if total_spend > 0 else None
    avg_ctr = round((total_clicks / total_impressions) * 100, 2) if total_impressions > 0 else None
    avg_cpa = round(total_spend / total_conversions, 2) if total_conversions > 0 else None

    return {
        "total_spend": round(total_spend, 2),
        "total_revenue": round(total_revenue, 2),
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "avg_roas": avg_roas,
        "avg_ctr": avg_ctr,
        "avg_cpa": avg_cpa,
    }


async def get_metrics_by_date_range(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[CampaignMetrics]:
    """
    Get all metrics within a date range across all user campaigns.

    Useful for chart data on the analytics dashboard.

    Args:
        db: Async database session.
        user_id: UUID of the user.
        start_date: Start of the date range (inclusive).
        end_date: End of the date range (inclusive).

    Returns:
        List of CampaignMetrics ordered by date ascending.
    """
    campaign_ids_query = select(Campaign.id).where(Campaign.user_id == user_id)
    campaign_ids_result = await db.execute(campaign_ids_query)
    campaign_ids = [row[0] for row in campaign_ids_result.all()]

    if not campaign_ids:
        return []

    result = await db.execute(
        select(CampaignMetrics)
        .where(
            CampaignMetrics.campaign_id.in_(campaign_ids),
            CampaignMetrics.date >= start_date,
            CampaignMetrics.date <= end_date,
        )
        .order_by(CampaignMetrics.date.asc())
    )
    return list(result.scalars().all())
