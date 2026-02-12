"""
Analytics service for aggregating social media engagement metrics.

Provides overview statistics, per-post metrics, and engagement rate
calculations across all of a user's published posts and social accounts.

For Developers:
    All functions accept `db: AsyncSession` and `user: User`. The overview
    aggregation uses SQL SUM/AVG for efficient computation. Per-post metrics
    are retrieved via JOIN between Posts and PostMetrics tables.

For QA Engineers:
    Test with users who have no posts (should return zero-filled response).
    Test with posts that have no metrics yet. Verify engagement rate
    calculation: (likes + comments + shares) / impressions.

For Project Managers:
    The analytics dashboard helps users understand their social media
    performance. Key metrics include impressions, reach, likes, comments,
    shares, clicks, and engagement rate.

For End Users:
    View your social media performance at a glance. Track which posts
    perform best and optimize your content strategy based on real data.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post, PostStatus
from app.models.post_metrics import PostMetrics
from app.models.user import User


async def get_analytics_overview(
    db: AsyncSession,
    user: User,
) -> dict:
    """
    Get aggregated analytics overview for all published posts.

    Calculates total and average metrics across all posts with metrics data.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        Dict with total_posts, total_impressions, total_reach, total_likes,
        total_comments, total_shares, total_clicks, and avg_engagement_rate.
    """
    # Count published posts
    posts_result = await db.execute(
        select(func.count(Post.id)).where(
            Post.user_id == user.id,
            Post.status == PostStatus.posted,
        )
    )
    total_posts = posts_result.scalar() or 0

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
        }

    # Aggregate metrics for user's posts
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
        .where(Post.user_id == user.id, Post.status == PostStatus.posted)
    )
    row = metrics_result.one()

    total_impressions = int(row.total_impressions)
    total_likes = int(row.total_likes)
    total_comments = int(row.total_comments)
    total_shares = int(row.total_shares)

    # Calculate average engagement rate
    avg_engagement_rate = 0.0
    if total_impressions > 0:
        avg_engagement_rate = round(
            (total_likes + total_comments + total_shares) / total_impressions * 100, 2
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
    }


async def get_post_metrics(
    db: AsyncSession,
    user: User,
    post_id: uuid.UUID,
) -> PostMetrics | None:
    """
    Get metrics for a specific post.

    Args:
        db: Async database session.
        user: The authenticated user.
        post_id: UUID of the post.

    Returns:
        PostMetrics record if found, None otherwise.
    """
    result = await db.execute(
        select(PostMetrics)
        .join(Post, PostMetrics.post_id == Post.id)
        .where(Post.id == post_id, Post.user_id == user.id)
    )
    return result.scalar_one_or_none()


async def get_all_post_metrics(
    db: AsyncSession,
    user: User,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict], int]:
    """
    Get metrics for all published posts with pagination.

    Returns post data alongside metrics data for the analytics table.

    Args:
        db: Async database session.
        user: The authenticated user.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Tuple of (list of metric dicts with post info, total count).
    """
    # Count total posts with metrics
    count_result = await db.execute(
        select(func.count(PostMetrics.id))
        .join(Post, PostMetrics.post_id == Post.id)
        .where(Post.user_id == user.id)
    )
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * per_page
    result = await db.execute(
        select(PostMetrics)
        .join(Post, PostMetrics.post_id == Post.id)
        .where(Post.user_id == user.id)
        .order_by(PostMetrics.fetched_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    metrics_list = result.scalars().all()

    items = []
    for m in metrics_list:
        engagement_rate = 0.0
        if m.impressions > 0:
            engagement_rate = round(
                (m.likes + m.comments + m.shares) / m.impressions * 100, 2
            )
        items.append({
            "id": m.id,
            "post_id": m.post_id,
            "impressions": m.impressions,
            "reach": m.reach,
            "likes": m.likes,
            "comments": m.comments,
            "shares": m.shares,
            "clicks": m.clicks,
            "engagement_rate": engagement_rate,
            "fetched_at": m.fetched_at,
        })

    return items, total
