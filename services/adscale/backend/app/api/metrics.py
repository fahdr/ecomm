"""
Campaign metrics and analytics API endpoints.

Provides endpoints for retrieving campaign performance metrics,
aggregated overview data, and date-range filtered analytics.

For Developers:
    Metrics are stored per-campaign per-day. The overview endpoint
    aggregates across all user campaigns. Date filtering uses ISO
    format (YYYY-MM-DD) query parameters.

For QA Engineers:
    Test: overview with no data (returns zeros), per-campaign metrics,
    date range filtering, pagination, authentication.

For Project Managers:
    Metrics endpoints power the analytics dashboard. Fast, accurate
    metric aggregation is critical for user experience.

For End Users:
    View performance metrics for your campaigns — track spend,
    revenue, ROAS, and more through the analytics dashboard.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.ads import MetricsOverview, MetricsResponse, PaginatedResponse
from app.services.metrics_service import (
    get_campaign_metrics,
    get_metrics_by_date_range,
    get_metrics_overview,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview", response_model=MetricsOverview)
async def get_overview_endpoint(
    start_date: date | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Filter to date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated metrics overview across all campaigns.

    Returns total spend, revenue, impressions, clicks, conversions,
    and average ROAS, CTR, CPA.

    Args:
        start_date: Optional start date filter (inclusive).
        end_date: Optional end date filter (inclusive).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        MetricsOverview with aggregated performance data.
    """
    overview = await get_metrics_overview(
        db, current_user.id, start_date, end_date
    )
    return MetricsOverview(**overview)


@router.get("/campaign/{campaign_id}", response_model=PaginatedResponse)
async def get_campaign_metrics_endpoint(
    campaign_id: str,
    start_date: date | None = Query(None, description="Filter from date"),
    end_date: date | None = Query(None, description="Filter to date"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(90, ge=1, le=365, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get daily metrics for a specific campaign.

    Returns paginated daily performance data (impressions, clicks,
    spend, revenue, ROAS, CPA, CTR) for the specified campaign.

    Args:
        campaign_id: UUID of the campaign.
        start_date: Optional start date filter (inclusive).
        end_date: Optional end date filter (inclusive).
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 90, max 365).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PaginatedResponse with daily metrics items.

    Raises:
        HTTPException 400: If campaign ID format is invalid.
    """
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    metrics, total = await get_campaign_metrics(
        db, cid, start_date, end_date, offset, limit
    )

    return PaginatedResponse(
        items=[MetricsResponse.model_validate(m) for m in metrics],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/date-range", response_model=list[MetricsResponse])
async def get_date_range_metrics_endpoint(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all metrics within a date range across all campaigns.

    Useful for building time-series charts on the analytics dashboard.
    Returns all matching metrics ordered by date ascending.

    Args:
        start_date: Start of the date range (inclusive, required).
        end_date: End of the date range (inclusive, required).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of MetricsResponse ordered by date ascending.
    """
    metrics = await get_metrics_by_date_range(
        db, current_user.id, start_date, end_date
    )
    return [MetricsResponse.model_validate(m) for m in metrics]
