"""
Analytics API routes for social media performance metrics.

Provides endpoints for viewing aggregated analytics overview and
per-post engagement metrics. All endpoints require authentication.

For Developers:
    The overview endpoint aggregates metrics across all published posts.
    Per-post metrics are retrieved with pagination. The engagement rate
    is calculated as (likes + comments + shares) / impressions * 100.

For QA Engineers:
    Test with: no posts (should return zero-filled), posts without metrics,
    posts with metrics. Verify pagination. Verify engagement rate formula.

For Project Managers:
    The analytics dashboard is a key feature for Pro and Enterprise users.
    It helps them understand social media performance and optimize strategy.

For End Users:
    View your overall social media performance or drill down into
    individual post metrics on the Analytics page.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.social import AnalyticsOverview, PostMetricsResponse
from app.services.analytics_service import (
    get_all_post_metrics,
    get_analytics_overview,
    get_post_metrics,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    summary="Get analytics overview",
)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated analytics overview for all published posts.

    Returns total metrics and average engagement rate across all
    of the user's published posts.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        AnalyticsOverview with totals and averages.
    """
    data = await get_analytics_overview(db=db, user=current_user)
    return AnalyticsOverview(**data)


@router.get(
    "/posts",
    response_model=list[PostMetricsResponse],
    summary="Get metrics for all posts",
)
async def get_all_metrics(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get engagement metrics for all published posts with pagination.

    Each metric record includes impressions, reach, likes, comments,
    shares, clicks, and a calculated engagement rate.

    Args:
        page: Page number (1-indexed).
        per_page: Items per page (max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of PostMetricsResponse records.
    """
    items, _ = await get_all_post_metrics(
        db=db, user=current_user, page=page, per_page=per_page
    )
    return [PostMetricsResponse(**item) for item in items]


@router.get(
    "/posts/{post_id}",
    response_model=PostMetricsResponse,
    summary="Get metrics for a single post",
)
async def get_single_post_metrics(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get engagement metrics for a specific post.

    Args:
        post_id: UUID of the post.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PostMetricsResponse with engagement data.

    Raises:
        HTTPException 404: If post or metrics not found.
    """
    metrics = await get_post_metrics(db=db, user=current_user, post_id=post_id)
    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics not found for this post",
        )

    engagement_rate = 0.0
    if metrics.impressions > 0:
        engagement_rate = round(
            (metrics.likes + metrics.comments + metrics.shares) / metrics.impressions * 100,
            2,
        )

    return PostMetricsResponse(
        id=metrics.id,
        post_id=metrics.post_id,
        impressions=metrics.impressions,
        reach=metrics.reach,
        likes=metrics.likes,
        comments=metrics.comments,
        shares=metrics.shares,
        clicks=metrics.clicks,
        engagement_rate=engagement_rate,
        fetched_at=metrics.fetched_at,
    )
