"""
Analytics API endpoints.

Provides aggregate email analytics across all campaigns and flows,
as well as per-campaign breakdowns.

For Developers:
    Analytics are computed from EmailEvent records and Campaign denormalized
    counters. Rates are percentages (0-100).

For QA Engineers:
    Test: aggregate analytics with no data (all zeros), with sent campaigns,
    rate calculations, per-campaign breakdown ordering.

For Project Managers:
    Analytics are the feedback loop — they help marketers understand
    what works and optimize future campaigns.

For End Users:
    View your overall email performance: sent, opened, clicked, bounced.
    Drill into individual campaigns for detailed analytics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.email import AggregateAnalytics
from app.services.analytics_service import get_aggregate_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AggregateAnalytics)
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregate email analytics for the authenticated user.

    Returns totals and rates across all campaigns, plus a per-campaign
    breakdown for campaigns that have been sent.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        AggregateAnalytics with totals, rates, and per-campaign data.
    """
    return await get_aggregate_analytics(db, current_user.id)
