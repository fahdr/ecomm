"""
Campaign performance tracking and analysis service.

Provides functions for recording daily metrics, computing time-series
performance data, and aggregating performance across campaigns and
ad accounts.

For Developers:
    ``record_metrics`` creates or updates daily metric records with
    auto-computed derived fields (ROAS, CPA, CTR).
    ``get_campaign_performance`` returns a combined time-series + totals
    dict suitable for dashboard charts.
    ``get_account_performance`` aggregates metrics across all campaigns
    on a given ad account.

For Project Managers:
    Performance tracking powers the analytics dashboard.  Accurate,
    fast aggregation is critical for users making budget decisions.

For QA Engineers:
    Test metric recording (create + update), derived field calculations,
    empty-data edge cases, date range filtering, and aggregate accuracy.
    Verify division-by-zero protection for ROAS/CPA/CTR.

For End Users:
    View your campaign performance in the Analytics section.  Track
    spend, revenue, ROAS, and other key metrics over time.
"""

import uuid
from datetime import date, timedelta

from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad_account import AdAccount
from app.models.campaign import Campaign
from app.models.campaign_metrics import CampaignMetrics


async def record_metrics(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    metrics_data: dict,
) -> CampaignMetrics:
    """
    Record (create or update) daily performance metrics for a campaign.

    Automatically computes derived fields: ROAS, CPA, and CTR from the
    base metrics (spend, revenue, impressions, clicks, conversions).

    Args:
        db: Async database session.
        campaign_id: UUID of the campaign.
        metrics_data: Dict with metric fields:
            - date (date): The date these metrics apply to.
            - impressions (int): Number of ad impressions.
            - clicks (int): Number of ad clicks.
            - conversions (int): Number of conversions.
            - spend (float): Total ad spend in USD.
            - revenue (float): Total attributed revenue in USD.

    Returns:
        The created or updated CampaignMetrics record.
    """
    metric_date = metrics_data.get("date", date.today())
    impressions = metrics_data.get("impressions", 0)
    clicks = metrics_data.get("clicks", 0)
    conversions = metrics_data.get("conversions", 0)
    spend = metrics_data.get("spend", 0.0)
    revenue = metrics_data.get("revenue", 0.0)

    # Compute derived metrics
    roas = round(revenue / spend, 4) if spend > 0 else None
    cpa = round(spend / conversions, 4) if conversions > 0 else None
    ctr = round((clicks / impressions) * 100, 4) if impressions > 0 else None

    # Check if a record already exists for this campaign + date
    result = await db.execute(
        select(CampaignMetrics).where(
            CampaignMetrics.campaign_id == campaign_id,
            CampaignMetrics.date == metric_date,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.impressions = impressions
        existing.clicks = clicks
        existing.conversions = conversions
        existing.spend = spend
        existing.revenue = revenue
        existing.roas = roas
        existing.cpa = cpa
        existing.ctr = ctr
        await db.flush()
        return existing

    metric = CampaignMetrics(
        campaign_id=campaign_id,
        date=metric_date,
        impressions=impressions,
        clicks=clicks,
        conversions=conversions,
        spend=spend,
        revenue=revenue,
        roas=roas,
        cpa=cpa,
        ctr=ctr,
    )
    db.add(metric)
    await db.flush()
    return metric


async def get_campaign_performance(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    days: int = 30,
) -> dict:
    """
    Get campaign performance with time-series and aggregated totals.

    Returns both daily data points for charting and summary totals
    for the specified time period.

    Args:
        db: Async database session.
        campaign_id: UUID of the campaign.
        days: Number of days to look back (default 30).

    Returns:
        Dict with:
            - time_series: List of daily metric dicts (date, impressions, etc.)
            - totals: Aggregated totals dict (total_spend, total_revenue, etc.)
            - period_days: Number of days in the reporting period.
    """
    start = date.today() - timedelta(days=days)

    # Fetch daily metrics
    result = await db.execute(
        select(CampaignMetrics)
        .where(
            CampaignMetrics.campaign_id == campaign_id,
            CampaignMetrics.date >= start,
        )
        .order_by(CampaignMetrics.date.asc())
    )
    metrics = list(result.scalars().all())

    # Build time series
    time_series = []
    for m in metrics:
        time_series.append({
            "date": m.date.isoformat(),
            "impressions": m.impressions,
            "clicks": m.clicks,
            "conversions": m.conversions,
            "spend": round(m.spend, 2),
            "revenue": round(m.revenue, 2),
            "roas": m.roas,
            "cpa": m.cpa,
            "ctr": m.ctr,
        })

    # Compute totals
    total_spend = sum(m.spend for m in metrics)
    total_revenue = sum(m.revenue for m in metrics)
    total_impressions = sum(m.impressions for m in metrics)
    total_clicks = sum(m.clicks for m in metrics)
    total_conversions = sum(m.conversions for m in metrics)

    totals = {
        "total_spend": round(total_spend, 2),
        "total_revenue": round(total_revenue, 2),
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "avg_roas": round(total_revenue / total_spend, 2) if total_spend > 0 else None,
        "avg_ctr": round((total_clicks / total_impressions) * 100, 2) if total_impressions > 0 else None,
        "avg_cpa": round(total_spend / total_conversions, 2) if total_conversions > 0 else None,
    }

    return {
        "time_series": time_series,
        "totals": totals,
        "period_days": days,
    }


async def get_account_performance(
    db: AsyncSession,
    ad_account_id: uuid.UUID,
    days: int = 30,
) -> dict:
    """
    Get aggregated performance across all campaigns on an ad account.

    Sums metrics from all campaigns associated with the given ad account
    for the specified time period.

    Args:
        db: Async database session.
        ad_account_id: UUID of the ad account.
        days: Number of days to look back (default 30).

    Returns:
        Dict with:
            - campaign_count: Number of campaigns on this account.
            - totals: Aggregated totals dict.
            - period_days: Number of days in the reporting period.
            - per_campaign: List of per-campaign summary dicts.
    """
    start = date.today() - timedelta(days=days)

    # Get all campaigns for this ad account
    campaign_result = await db.execute(
        select(Campaign).where(Campaign.ad_account_id == ad_account_id)
    )
    campaigns = list(campaign_result.scalars().all())

    if not campaigns:
        return {
            "campaign_count": 0,
            "totals": {
                "total_spend": 0.0,
                "total_revenue": 0.0,
                "total_impressions": 0,
                "total_clicks": 0,
                "total_conversions": 0,
                "avg_roas": None,
                "avg_ctr": None,
                "avg_cpa": None,
            },
            "period_days": days,
            "per_campaign": [],
        }

    campaign_ids = [c.id for c in campaigns]

    # Aggregate metrics
    agg_result = await db.execute(
        select(
            sql_func.coalesce(sql_func.sum(CampaignMetrics.spend), 0.0).label("total_spend"),
            sql_func.coalesce(sql_func.sum(CampaignMetrics.revenue), 0.0).label("total_revenue"),
            sql_func.coalesce(sql_func.sum(CampaignMetrics.impressions), 0).label("total_impressions"),
            sql_func.coalesce(sql_func.sum(CampaignMetrics.clicks), 0).label("total_clicks"),
            sql_func.coalesce(sql_func.sum(CampaignMetrics.conversions), 0).label("total_conversions"),
        ).where(
            CampaignMetrics.campaign_id.in_(campaign_ids),
            CampaignMetrics.date >= start,
        )
    )
    row = agg_result.one()

    total_spend = float(row.total_spend)
    total_revenue = float(row.total_revenue)
    total_impressions = int(row.total_impressions)
    total_clicks = int(row.total_clicks)
    total_conversions = int(row.total_conversions)

    totals = {
        "total_spend": round(total_spend, 2),
        "total_revenue": round(total_revenue, 2),
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "avg_roas": round(total_revenue / total_spend, 2) if total_spend > 0 else None,
        "avg_ctr": round((total_clicks / total_impressions) * 100, 2) if total_impressions > 0 else None,
        "avg_cpa": round(total_spend / total_conversions, 2) if total_conversions > 0 else None,
    }

    # Per-campaign breakdowns
    per_campaign = []
    for campaign in campaigns:
        camp_result = await db.execute(
            select(
                sql_func.coalesce(sql_func.sum(CampaignMetrics.spend), 0.0).label("spend"),
                sql_func.coalesce(sql_func.sum(CampaignMetrics.revenue), 0.0).label("revenue"),
                sql_func.coalesce(sql_func.sum(CampaignMetrics.conversions), 0).label("conversions"),
            ).where(
                CampaignMetrics.campaign_id == campaign.id,
                CampaignMetrics.date >= start,
            )
        )
        crow = camp_result.one()
        camp_spend = float(crow.spend)
        camp_revenue = float(crow.revenue)
        camp_conversions = int(crow.conversions)

        per_campaign.append({
            "campaign_id": str(campaign.id),
            "campaign_name": campaign.name,
            "spend": round(camp_spend, 2),
            "revenue": round(camp_revenue, 2),
            "conversions": camp_conversions,
            "roas": round(camp_revenue / camp_spend, 2) if camp_spend > 0 else None,
        })

    return {
        "campaign_count": len(campaigns),
        "totals": totals,
        "period_days": days,
        "per_campaign": per_campaign,
    }
