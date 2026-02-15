"""
Automated campaign optimization and analysis service.

Analyzes campaign performance against benchmarks and thresholds to
generate actionable optimization recommendations.  Supports both
single-campaign analysis and batch optimization across all active
campaigns for a user.

For Developers:
    ``analyze_campaign`` checks a single campaign's metrics against
    industry benchmarks and returns an ``OptimizationRecommendation``.
    ``auto_optimize`` batch-processes all active campaigns for a user.
    Both functions use the most recent 7 days of metrics data.

For Project Managers:
    Auto-optimization is a premium feature that helps users manage
    campaigns without constant manual monitoring.  It identifies
    underperforming campaigns and suggests concrete actions.

For QA Engineers:
    Test all recommendation scenarios: pause (low ROAS), scale (high ROAS),
    adjust_bid (low CTR), change_targeting (high CPA).  Test edge cases:
    no metrics, zero spend, brand-new campaigns.  Verify confidence scores.

For End Users:
    Enable auto-optimization to let AdScale continuously monitor and
    improve your campaigns.  Review recommendations before they are
    applied, or let them run automatically.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_metrics import CampaignMetrics


# ── Benchmark Thresholds ──────────────────────────────────────────────

BENCHMARKS = {
    "roas_minimum": 1.0,
    "roas_good": 3.0,
    "roas_excellent": 5.0,
    "ctr_minimum": 1.0,
    "ctr_good": 2.5,
    "cpa_maximum": 50.0,
    "cpa_good": 20.0,
}


# ── Data Classes ──────────────────────────────────────────────────────


@dataclass
class OptimizationRecommendation:
    """
    An optimization recommendation for a campaign.

    Attributes:
        campaign_id: UUID of the analyzed campaign.
        campaign_name: Name of the campaign.
        action: Recommended action ('pause', 'scale', 'adjust_bid',
                'change_targeting', 'no_action', 'insufficient_data').
        reason: Human-readable explanation of why this action is recommended.
        confidence: Confidence score from 0.0 to 1.0.
        suggested_budget: Suggested new daily budget (None if not applicable).
        metrics_summary: Dict with the recent metrics used for analysis.
    """

    campaign_id: uuid.UUID
    campaign_name: str
    action: str
    reason: str
    confidence: float
    suggested_budget: float | None = None
    metrics_summary: dict | None = None


# ── Core Analysis ─────────────────────────────────────────────────────


async def _get_recent_metrics(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    days: int = 7,
) -> list[CampaignMetrics]:
    """
    Fetch the most recent N days of metrics for a campaign.

    Args:
        db: Async database session.
        campaign_id: UUID of the campaign.
        days: Number of days to look back (default 7).

    Returns:
        List of CampaignMetrics ordered by date descending.
    """
    start = date.today() - timedelta(days=days)
    result = await db.execute(
        select(CampaignMetrics)
        .where(
            CampaignMetrics.campaign_id == campaign_id,
            CampaignMetrics.date >= start,
        )
        .order_by(CampaignMetrics.date.desc())
    )
    return list(result.scalars().all())


def _compute_averages(metrics: list[CampaignMetrics]) -> dict:
    """
    Compute average performance metrics from a list of daily records.

    Args:
        metrics: List of CampaignMetrics records.

    Returns:
        Dict with avg_roas, avg_ctr, avg_cpa, total_spend, total_revenue,
        total_impressions, total_clicks, total_conversions.
    """
    if not metrics:
        return {
            "avg_roas": None,
            "avg_ctr": None,
            "avg_cpa": None,
            "total_spend": 0.0,
            "total_revenue": 0.0,
            "total_impressions": 0,
            "total_clicks": 0,
            "total_conversions": 0,
        }

    total_spend = sum(m.spend for m in metrics)
    total_revenue = sum(m.revenue for m in metrics)
    total_impressions = sum(m.impressions for m in metrics)
    total_clicks = sum(m.clicks for m in metrics)
    total_conversions = sum(m.conversions for m in metrics)

    avg_roas = round(total_revenue / total_spend, 2) if total_spend > 0 else None
    avg_ctr = round((total_clicks / total_impressions) * 100, 2) if total_impressions > 0 else None
    avg_cpa = round(total_spend / total_conversions, 2) if total_conversions > 0 else None

    return {
        "avg_roas": avg_roas,
        "avg_ctr": avg_ctr,
        "avg_cpa": avg_cpa,
        "total_spend": round(total_spend, 2),
        "total_revenue": round(total_revenue, 2),
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
    }


async def analyze_campaign(
    db: AsyncSession,
    campaign_id: uuid.UUID,
) -> OptimizationRecommendation:
    """
    Analyze a campaign's performance and generate an optimization recommendation.

    Checks the campaign's most recent 7 days of metrics against benchmark
    thresholds and recommends one of: pause, scale, adjust_bid,
    change_targeting, or no_action.

    Args:
        db: Async database session.
        campaign_id: UUID of the campaign to analyze.

    Returns:
        OptimizationRecommendation with the suggested action, reason,
        confidence score, and optional budget suggestion.

    Raises:
        ValueError: If the campaign is not found.
    """
    # Fetch campaign
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise ValueError("Campaign not found.")

    # Fetch recent metrics
    metrics = await _get_recent_metrics(db, campaign_id)
    averages = _compute_averages(metrics)

    # Insufficient data
    if not metrics or averages["total_spend"] == 0:
        return OptimizationRecommendation(
            campaign_id=campaign_id,
            campaign_name=campaign.name,
            action="insufficient_data",
            reason="Not enough performance data to make recommendations. "
                   "Run the campaign for at least 3 days with spend.",
            confidence=0.0,
            metrics_summary=averages,
        )

    avg_roas = averages["avg_roas"]
    avg_ctr = averages["avg_ctr"]
    avg_cpa = averages["avg_cpa"]

    # Decision tree: ordered by severity
    # 1. Very low ROAS -> pause
    if avg_roas is not None and avg_roas < BENCHMARKS["roas_minimum"]:
        return OptimizationRecommendation(
            campaign_id=campaign_id,
            campaign_name=campaign.name,
            action="pause",
            reason=f"ROAS ({avg_roas:.2f}) is below minimum threshold "
                   f"({BENCHMARKS['roas_minimum']}). Pausing to prevent "
                   f"further budget waste.",
            confidence=0.9,
            metrics_summary=averages,
        )

    # 2. High CPA -> change targeting
    if avg_cpa is not None and avg_cpa > BENCHMARKS["cpa_maximum"]:
        return OptimizationRecommendation(
            campaign_id=campaign_id,
            campaign_name=campaign.name,
            action="change_targeting",
            reason=f"CPA (${avg_cpa:.2f}) exceeds maximum threshold "
                   f"(${BENCHMARKS['cpa_maximum']:.2f}). Consider narrowing "
                   f"your targeting to reach more qualified audiences.",
            confidence=0.75,
            metrics_summary=averages,
        )

    # 3. Low CTR -> adjust bids
    if avg_ctr is not None and avg_ctr < BENCHMARKS["ctr_minimum"]:
        return OptimizationRecommendation(
            campaign_id=campaign_id,
            campaign_name=campaign.name,
            action="adjust_bid",
            reason=f"CTR ({avg_ctr:.2f}%) is below minimum threshold "
                   f"({BENCHMARKS['ctr_minimum']}%). Consider refreshing "
                   f"ad creatives or adjusting bid strategy.",
            confidence=0.7,
            metrics_summary=averages,
        )

    # 4. Excellent ROAS -> scale up
    if avg_roas is not None and avg_roas >= BENCHMARKS["roas_excellent"]:
        suggested_budget = round(campaign.budget_daily * 1.5, 2) if campaign.budget_daily else None
        return OptimizationRecommendation(
            campaign_id=campaign_id,
            campaign_name=campaign.name,
            action="scale",
            reason=f"Excellent ROAS ({avg_roas:.2f}) exceeds {BENCHMARKS['roas_excellent']}. "
                   f"Scaling budget by 50% to capture more conversions.",
            confidence=0.85,
            suggested_budget=suggested_budget,
            metrics_summary=averages,
        )

    # 5. Good ROAS -> moderate scale
    if avg_roas is not None and avg_roas >= BENCHMARKS["roas_good"]:
        suggested_budget = round(campaign.budget_daily * 1.2, 2) if campaign.budget_daily else None
        return OptimizationRecommendation(
            campaign_id=campaign_id,
            campaign_name=campaign.name,
            action="scale",
            reason=f"Good ROAS ({avg_roas:.2f}) above {BENCHMARKS['roas_good']}. "
                   f"Increasing budget by 20% for growth.",
            confidence=0.7,
            suggested_budget=suggested_budget,
            metrics_summary=averages,
        )

    # 6. Everything is fine
    return OptimizationRecommendation(
        campaign_id=campaign_id,
        campaign_name=campaign.name,
        action="no_action",
        reason="Campaign is performing within acceptable ranges. "
               "No optimization needed at this time.",
        confidence=0.6,
        metrics_summary=averages,
    )


async def auto_optimize(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict]:
    """
    Batch-analyze all active campaigns for a user and return recommendations.

    Fetches all campaigns with 'active' status, analyzes each, and returns
    a list of recommendation dicts.

    Args:
        db: Async database session.
        user_id: UUID of the user.

    Returns:
        List of dicts, each containing:
            - campaign_id: UUID string.
            - campaign_name: Campaign name.
            - action: Recommended action.
            - reason: Explanation.
            - confidence: Score (0-1).
            - suggested_budget: Optional new budget.
    """
    result = await db.execute(
        select(Campaign).where(
            Campaign.user_id == user_id,
            Campaign.status == CampaignStatus.active,
        )
    )
    campaigns = list(result.scalars().all())

    recommendations = []
    for campaign in campaigns:
        rec = await analyze_campaign(db, campaign.id)
        recommendations.append({
            "campaign_id": str(rec.campaign_id),
            "campaign_name": rec.campaign_name,
            "action": rec.action,
            "reason": rec.reason,
            "confidence": rec.confidence,
            "suggested_budget": rec.suggested_budget,
        })

    return recommendations
