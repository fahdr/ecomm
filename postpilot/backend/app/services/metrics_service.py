"""
Metrics tracking service for social media post performance.

Provides functions for recording engagement metrics snapshots, retrieving
per-post performance data, and computing aggregated account analytics.

For Developers:
    ``record_metrics`` creates or updates a PostMetrics record for a post.
    ``get_post_performance`` returns a dict with all metrics and computed
    engagement rate. ``get_account_analytics`` aggregates metrics across
    all posts for a given social account within a date range.

For QA Engineers:
    Test metric recording with valid and invalid post IDs. Verify that
    engagement rate is calculated correctly:
    ``(likes + comments + shares) / impressions * 100``.
    Test that recording metrics updates existing records (upsert behavior).

For Project Managers:
    Metrics tracking powers the Analytics dashboard, giving users insight
    into which posts and platforms perform best for their audience.

For End Users:
    Track how each post performs with real engagement metrics. View
    detailed analytics to optimize your content strategy.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post, PostStatus
from app.models.post_metrics import PostMetrics


async def record_metrics(
    db: AsyncSession,
    post_id: uuid.UUID,
    metrics_data: dict,
) -> PostMetrics:
    """
    Record or update engagement metrics for a post.

    If a PostMetrics record already exists for the post, it is updated.
    Otherwise, a new record is created. This implements upsert behavior.

    Args:
        db: Async database session.
        post_id: UUID of the post to record metrics for.
        metrics_data: Dict with keys: impressions, reach, likes,
                      comments, shares, clicks.

    Returns:
        The created or updated PostMetrics record.

    Raises:
        ValueError: If the post does not exist.
    """
    # Verify post exists
    post_result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = post_result.scalar_one_or_none()
    if not post:
        raise ValueError(f"Post {post_id} not found")

    # Check for existing metrics
    result = await db.execute(
        select(PostMetrics).where(PostMetrics.post_id == post_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing metrics
        existing.impressions = metrics_data.get("impressions", existing.impressions)
        existing.reach = metrics_data.get("reach", existing.reach)
        existing.likes = metrics_data.get("likes", existing.likes)
        existing.comments = metrics_data.get("comments", existing.comments)
        existing.shares = metrics_data.get("shares", existing.shares)
        existing.clicks = metrics_data.get("clicks", existing.clicks)
        existing.fetched_at = datetime.now(UTC)
        await db.flush()
        return existing
    else:
        # Create new metrics record
        metrics = PostMetrics(
            post_id=post_id,
            impressions=metrics_data.get("impressions", 0),
            reach=metrics_data.get("reach", 0),
            likes=metrics_data.get("likes", 0),
            comments=metrics_data.get("comments", 0),
            shares=metrics_data.get("shares", 0),
            clicks=metrics_data.get("clicks", 0),
        )
        db.add(metrics)
        await db.flush()
        return metrics


async def get_post_performance(
    db: AsyncSession,
    post_id: uuid.UUID,
) -> dict | None:
    """
    Get performance data for a specific post including computed engagement rate.

    Args:
        db: Async database session.
        post_id: UUID of the post.

    Returns:
        Dict with all metrics fields plus 'engagement_rate', or None if
        no metrics exist for the post.
    """
    result = await db.execute(
        select(PostMetrics).where(PostMetrics.post_id == post_id)
    )
    metrics = result.scalar_one_or_none()

    if not metrics:
        return None

    engagement_rate = 0.0
    if metrics.impressions > 0:
        engagement_rate = round(
            (metrics.likes + metrics.comments + metrics.shares)
            / metrics.impressions * 100,
            2,
        )

    return {
        "id": metrics.id,
        "post_id": metrics.post_id,
        "impressions": metrics.impressions,
        "reach": metrics.reach,
        "likes": metrics.likes,
        "comments": metrics.comments,
        "shares": metrics.shares,
        "clicks": metrics.clicks,
        "engagement_rate": engagement_rate,
        "fetched_at": metrics.fetched_at,
    }


async def get_account_analytics(
    db: AsyncSession,
    account_id: uuid.UUID,
    days: int = 30,
) -> dict:
    """
    Get aggregated analytics for a social account over a date range.

    Aggregates engagement metrics across all published posts for the
    specified account within the last N days.

    Args:
        db: Async database session.
        account_id: UUID of the social account.
        days: Number of days to look back (default: 30).

    Returns:
        Dict with aggregated metrics: total_posts, total_impressions,
        total_reach, total_likes, total_comments, total_shares,
        total_clicks, avg_engagement_rate, and period_days.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Count posts in period
    post_count_result = await db.execute(
        select(func.count(Post.id)).where(
            Post.account_id == account_id,
            Post.status == PostStatus.posted,
            Post.posted_at >= cutoff,
        )
    )
    total_posts = post_count_result.scalar() or 0

    if total_posts == 0:
        return {
            "total_posts": 0,
            "total_impressions": 0,
            "total_reach": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "total_clicks": 0,
            "avg_engagement_rate": 0.0,
            "period_days": days,
        }

    # Aggregate metrics for account posts in period
    metrics_result = await db.execute(
        select(
            func.coalesce(func.sum(PostMetrics.impressions), 0).label("total_impressions"),
            func.coalesce(func.sum(PostMetrics.reach), 0).label("total_reach"),
            func.coalesce(func.sum(PostMetrics.likes), 0).label("total_likes"),
            func.coalesce(func.sum(PostMetrics.comments), 0).label("total_comments"),
            func.coalesce(func.sum(PostMetrics.shares), 0).label("total_shares"),
            func.coalesce(func.sum(PostMetrics.clicks), 0).label("total_clicks"),
        )
        .join(Post, PostMetrics.post_id == Post.id)
        .where(
            Post.account_id == account_id,
            Post.status == PostStatus.posted,
            Post.posted_at >= cutoff,
        )
    )
    row = metrics_result.one()

    total_impressions = int(row.total_impressions)
    total_likes = int(row.total_likes)
    total_comments = int(row.total_comments)
    total_shares = int(row.total_shares)

    avg_engagement_rate = 0.0
    if total_impressions > 0:
        avg_engagement_rate = round(
            (total_likes + total_comments + total_shares) / total_impressions * 100,
            2,
        )

    return {
        "total_posts": total_posts,
        "total_impressions": total_impressions,
        "total_reach": int(row.total_reach),
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "total_clicks": int(row.total_clicks),
        "avg_engagement_rate": avg_engagement_rate,
        "period_days": days,
    }
