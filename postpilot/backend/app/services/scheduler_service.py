"""
Scheduling engine for social media posts.

Provides functions for scheduling posts, retrieving upcoming posts,
simulated publishing, and optimal time suggestions per platform.

For Developers:
    ``schedule_post`` creates or updates a post's scheduled time and sets
    its status to 'scheduled'. ``get_upcoming_posts`` returns all posts
    scheduled within the next N days. ``publish_post`` simulates publishing
    by updating the post status and logging to console. ``get_best_times``
    returns hardcoded optimal posting times per platform.

For QA Engineers:
    Test scheduling with past dates (should raise ValueError), future dates
    (should succeed), timezone handling, and that publish_post correctly
    transitions the status from 'scheduled' to 'posted'.

For Project Managers:
    The scheduling engine is the core of PostPilot's automation. It lets
    users queue content in advance and publish at optimal times for
    maximum engagement.

For End Users:
    Schedule your posts for the best times to reach your audience.
    PostPilot suggests optimal times based on platform-specific data.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post, PostStatus

logger = logging.getLogger(__name__)

# Hardcoded optimal posting times per platform (hour in UTC)
# Based on general social media best practices
OPTIMAL_TIMES: dict[str, list[dict[str, str]]] = {
    "instagram": [
        {"time": "11:00", "label": "Late morning (highest engagement)"},
        {"time": "14:00", "label": "Early afternoon"},
        {"time": "19:00", "label": "Evening (commute time)"},
    ],
    "facebook": [
        {"time": "09:00", "label": "Morning (work start)"},
        {"time": "13:00", "label": "Lunch break"},
        {"time": "16:00", "label": "Afternoon wind-down"},
    ],
    "tiktok": [
        {"time": "07:00", "label": "Early morning scroll"},
        {"time": "12:00", "label": "Lunch break"},
        {"time": "22:00", "label": "Late night (peak TikTok)"},
    ],
    "twitter": [
        {"time": "08:00", "label": "Morning news check"},
        {"time": "12:00", "label": "Lunch break"},
        {"time": "17:00", "label": "End of workday"},
    ],
    "pinterest": [
        {"time": "14:00", "label": "Afternoon browsing"},
        {"time": "20:00", "label": "Evening planning"},
        {"time": "21:00", "label": "Night browsing"},
    ],
}


async def schedule_post(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    content: str,
    media_urls: list[str],
    scheduled_at: datetime,
    platform: str = "instagram",
    hashtags: list[str] | None = None,
) -> Post:
    """
    Create and schedule a new post for future publication.

    Creates a new Post record with status 'scheduled' and the provided
    scheduled_at timestamp.

    Args:
        db: Async database session.
        user_id: UUID of the post owner.
        account_id: UUID of the target social account.
        content: Post caption text.
        media_urls: List of media attachment URLs.
        scheduled_at: When the post should be published.
        platform: Target social media platform.
        hashtags: Optional list of hashtags.

    Returns:
        The newly created Post with status='scheduled'.

    Raises:
        ValueError: If scheduled_at is in the past.
    """
    if scheduled_at < datetime.now(UTC):
        raise ValueError("Cannot schedule a post in the past")

    post = Post(
        user_id=user_id,
        account_id=account_id,
        content=content,
        media_urls=media_urls,
        hashtags=hashtags or [],
        platform=platform,
        status=PostStatus.scheduled,
        scheduled_for=scheduled_at,
    )
    db.add(post)
    await db.flush()
    return post


async def get_upcoming_posts(
    db: AsyncSession,
    user_id: uuid.UUID,
    days: int = 7,
) -> list[Post]:
    """
    Retrieve all posts scheduled within the next N days.

    Args:
        db: Async database session.
        user_id: UUID of the post owner.
        days: Number of days ahead to look (default: 7).

    Returns:
        List of Post records scheduled within the time window,
        ordered by scheduled_for ascending.
    """
    now = datetime.now(UTC)
    cutoff = now + timedelta(days=days)

    result = await db.execute(
        select(Post)
        .where(
            Post.user_id == user_id,
            Post.status == PostStatus.scheduled,
            Post.scheduled_for >= now,
            Post.scheduled_for <= cutoff,
        )
        .order_by(Post.scheduled_for.asc())
    )
    return list(result.scalars().all())


async def publish_post(
    db: AsyncSession,
    post_id: uuid.UUID,
) -> bool:
    """
    Simulate publishing a scheduled post.

    In development mode, logs the publish action to console. In production,
    this would call the platform's API to publish the content.

    Args:
        db: Async database session.
        post_id: UUID of the post to publish.

    Returns:
        True if the post was successfully published, False otherwise.
    """
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        logger.error("Post %s not found for publishing", post_id)
        return False

    if post.status != PostStatus.scheduled:
        logger.warning("Post %s is not in scheduled status (current: %s)", post_id, post.status)
        return False

    # Simulate publishing
    logger.info(
        "Publishing post %s to %s: %.100s...",
        post_id,
        post.platform,
        post.content,
    )

    post.status = PostStatus.posted
    post.posted_at = datetime.now(UTC)
    await db.flush()

    logger.info("Post %s published successfully at %s", post_id, post.posted_at)
    return True


def get_best_times(platform: str) -> list[dict[str, str]]:
    """
    Get suggested optimal posting times for a platform.

    Returns hardcoded best times based on general social media engagement
    data. Each time includes a human-readable label.

    Args:
        platform: The social media platform.

    Returns:
        List of dicts with 'time' (HH:MM) and 'label' keys.
    """
    return OPTIMAL_TIMES.get(platform, OPTIMAL_TIMES["instagram"])


def get_next_optimal_time(platform: str, base_date: datetime | None = None) -> datetime:
    """
    Calculate the next optimal posting time for a platform from a base date.

    Picks the first optimal time that is in the future from the base date.
    If no time is available today, uses tomorrow's first optimal time.

    Args:
        platform: The social media platform.
        base_date: The starting date/time to search from (default: now UTC).

    Returns:
        A datetime representing the next optimal posting time.
    """
    if base_date is None:
        base_date = datetime.now(UTC)

    best_times = get_best_times(platform)

    for time_info in best_times:
        hour, minute = map(int, time_info["time"].split(":"))
        candidate = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > base_date:
            return candidate

    # If no time found today, use first time tomorrow
    tomorrow = base_date + timedelta(days=1)
    first_hour, first_minute = map(int, best_times[0]["time"].split(":"))
    return tomorrow.replace(hour=first_hour, minute=first_minute, second=0, microsecond=0)
