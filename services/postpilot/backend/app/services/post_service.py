"""
Post management service for CRUD operations, scheduling, and plan enforcement.

Handles the full post lifecycle: create draft, update, schedule, retrieve,
delete, and calendar views. Enforces plan limits on posts per month.

For Developers:
    All functions accept `db: AsyncSession` and `user: User`. Post creation
    checks the `max_items` (posts per month) limit from the user's plan.
    The `schedule_post` function sets the status to "scheduled" and assigns
    the scheduled_for timestamp. The calendar view groups posts by date.

For QA Engineers:
    Test plan limits for post creation. Test scheduling with past dates
    (should be rejected). Test pagination (page, per_page parameters).
    Test calendar view with various date ranges.

For Project Managers:
    Posts are the core content unit. Users create, schedule, and track
    posts through the Queue and Calendar views.

For End Users:
    Create posts with captions, media, and hashtags. Schedule them for
    optimal times, or save as drafts to publish later.
"""

import uuid
from collections import defaultdict
from datetime import UTC, datetime, date

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PLAN_LIMITS
from app.models.post import Post, PostStatus
from app.models.user import User


async def create_post(
    db: AsyncSession,
    user: User,
    account_id: uuid.UUID,
    content: str,
    platform: str,
    media_urls: list[str] | None = None,
    hashtags: list[str] | None = None,
    scheduled_for: datetime | None = None,
) -> Post:
    """
    Create a new social media post.

    Enforces the plan's max_items limit (posts per month). If a
    scheduled_for time is provided, the post status is set to "scheduled";
    otherwise it defaults to "draft".

    Args:
        db: Async database session.
        user: The authenticated user.
        account_id: Target social account UUID.
        content: Post caption text.
        platform: Target platform string.
        media_urls: Optional list of media URLs.
        hashtags: Optional list of hashtags.
        scheduled_for: Optional scheduled publish time.

    Returns:
        The newly created Post.

    Raises:
        ValueError: If the user has reached their monthly post limit.
    """
    # Check plan limit for posts this month
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_items != -1:
        today = datetime.now(UTC)
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(func.count(Post.id)).where(
                Post.user_id == user.id,
                Post.created_at >= month_start,
            )
        )
        current_count = result.scalar() or 0
        if current_count >= plan_limits.max_items:
            raise ValueError(
                f"Monthly post limit reached ({plan_limits.max_items} posts). "
                "Upgrade your plan to create more posts."
            )

    status = PostStatus.scheduled if scheduled_for else PostStatus.draft

    post = Post(
        user_id=user.id,
        account_id=account_id,
        content=content,
        platform=platform,
        media_urls=media_urls or [],
        hashtags=hashtags or [],
        status=status,
        scheduled_for=scheduled_for,
    )
    db.add(post)
    await db.flush()
    return post


async def update_post(
    db: AsyncSession,
    user: User,
    post_id: uuid.UUID,
    content: str | None = None,
    media_urls: list[str] | None = None,
    hashtags: list[str] | None = None,
    scheduled_for: datetime | None = ...,
) -> Post:
    """
    Update an existing post (partial update).

    Only draft and scheduled posts can be updated. Posted or failed posts
    are immutable. Uses the Ellipsis sentinel to distinguish "not provided"
    from `None` for the scheduled_for field.

    Args:
        db: Async database session.
        user: The authenticated user.
        post_id: UUID of the post to update.
        content: Updated caption text (None = no change).
        media_urls: Updated media URLs (None = no change).
        hashtags: Updated hashtags (None = no change).
        scheduled_for: Updated schedule time (Ellipsis = no change, None = clear schedule).

    Returns:
        The updated Post.

    Raises:
        ValueError: If post not found, not owned by user, or already posted/failed.
    """
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.user_id == user.id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise ValueError("Post not found")

    if post.status in (PostStatus.posted, PostStatus.failed):
        raise ValueError("Cannot update a post that has been posted or failed")

    if content is not None:
        post.content = content
    if media_urls is not None:
        post.media_urls = media_urls
    if hashtags is not None:
        post.hashtags = hashtags
    if scheduled_for is not ...:
        post.scheduled_for = scheduled_for
        post.status = PostStatus.scheduled if scheduled_for else PostStatus.draft

    await db.flush()
    return post


async def delete_post(
    db: AsyncSession,
    user: User,
    post_id: uuid.UUID,
) -> None:
    """
    Delete a post permanently.

    Only draft and scheduled posts can be deleted. Posted posts are
    kept for analytics history.

    Args:
        db: Async database session.
        user: The authenticated user.
        post_id: UUID of the post to delete.

    Raises:
        ValueError: If post not found, not owned by user, or already posted.
    """
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.user_id == user.id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise ValueError("Post not found")

    if post.status == PostStatus.posted:
        raise ValueError("Cannot delete a published post")

    await db.delete(post)
    await db.flush()


async def get_post(
    db: AsyncSession,
    user: User,
    post_id: uuid.UUID,
) -> Post | None:
    """
    Get a single post by ID.

    Args:
        db: Async database session.
        user: The authenticated user.
        post_id: UUID of the post to retrieve.

    Returns:
        The Post if found and belongs to user, None otherwise.
    """
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.user_id == user.id)
    )
    return result.scalar_one_or_none()


async def list_posts(
    db: AsyncSession,
    user: User,
    page: int = 1,
    per_page: int = 20,
    status: PostStatus | None = None,
    platform: str | None = None,
) -> tuple[list[Post], int]:
    """
    List posts with pagination and optional filtering.

    Args:
        db: Async database session.
        user: The authenticated user.
        page: Page number (1-indexed).
        per_page: Items per page.
        status: Optional status filter.
        platform: Optional platform filter.

    Returns:
        Tuple of (posts list, total count).
    """
    conditions = [Post.user_id == user.id]
    if status:
        conditions.append(Post.status == status)
    if platform:
        conditions.append(Post.platform == platform)

    # Count total
    count_query = select(func.count(Post.id)).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * per_page
    query = (
        select(Post)
        .where(and_(*conditions))
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    posts = list(result.scalars().all())

    return posts, total


async def schedule_post(
    db: AsyncSession,
    user: User,
    post_id: uuid.UUID,
    scheduled_for: datetime,
) -> Post:
    """
    Schedule a draft post for future publication.

    Args:
        db: Async database session.
        user: The authenticated user.
        post_id: UUID of the post to schedule.
        scheduled_for: When to publish the post.

    Returns:
        The updated Post with status=scheduled.

    Raises:
        ValueError: If post not found, not a draft, or scheduled_for is in the past.
    """
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.user_id == user.id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise ValueError("Post not found")

    if post.status not in (PostStatus.draft, PostStatus.scheduled):
        raise ValueError("Only draft or scheduled posts can be (re)scheduled")

    if scheduled_for < datetime.now(UTC):
        raise ValueError("Cannot schedule a post in the past")

    post.scheduled_for = scheduled_for
    post.status = PostStatus.scheduled
    await db.flush()
    return post


async def get_calendar_posts(
    db: AsyncSession,
    user: User,
    start_date: date,
    end_date: date,
) -> dict[str, list[Post]]:
    """
    Get posts grouped by date for calendar view.

    Args:
        db: Async database session.
        user: The authenticated user.
        start_date: Calendar start date (inclusive).
        end_date: Calendar end date (inclusive).

    Returns:
        Dict mapping ISO date strings to lists of posts.
    """
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    result = await db.execute(
        select(Post)
        .where(
            Post.user_id == user.id,
            Post.scheduled_for.isnot(None),
            Post.scheduled_for >= start_dt,
            Post.scheduled_for <= end_dt,
        )
        .order_by(Post.scheduled_for.asc())
    )
    posts = result.scalars().all()

    # Group by date
    grouped: dict[str, list[Post]] = defaultdict(list)
    for post in posts:
        if post.scheduled_for:
            day_key = post.scheduled_for.strftime("%Y-%m-%d")
            grouped[day_key].append(post)

    return dict(grouped)
