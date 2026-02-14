"""
Post management API routes.

Provides CRUD endpoints for social media posts, scheduling, calendar
views, product-to-post pipeline, and metrics recording. All endpoints
require authentication via JWT Bearer token.

For Developers:
    Post creation enforces plan limits (max_items = posts/month). The
    calendar endpoint accepts start_date/end_date query parameters and
    returns posts grouped by date with suggested posting times.
    The from-product endpoint generates posts from product data.
    The metrics endpoint records engagement data for posts.

For QA Engineers:
    Test: create post (201), list with pagination, update draft, schedule,
    delete draft, calendar view with date range, plan limit enforcement (403),
    product-to-post pipeline, metrics recording.

For Project Managers:
    These endpoints power the Queue and Calendar pages. Posts are the
    core content unit that users create, schedule, and track.

For End Users:
    Create and manage your social media posts. Schedule them for the best
    time or save as drafts to publish later.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.post import PostStatus
from app.models.user import User
from app.schemas.social import (
    CalendarDay,
    CalendarView,
    MetricsRecordRequest,
    PostCreate,
    PostListResponse,
    PostMetricsResponse,
    PostResponse,
    PostSchedule,
    PostUpdate,
    ProductToPostRequest,
    ProductToPostResponse,
    SuggestedTime,
)
from app.services.post_service import (
    create_post,
    delete_post,
    get_calendar_posts,
    get_post,
    list_posts,
    schedule_post,
    update_post,
)
from app.services.product_post_service import product_to_posts
from app.services.metrics_service import record_metrics, get_post_performance
from app.services.scheduler_service import get_best_times

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post(
    "/from-product",
    response_model=ProductToPostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate posts from product data",
)
async def create_posts_from_product(
    payload: ProductToPostRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate social media posts from product data across multiple platforms.

    Uses the product-to-post pipeline to generate platform-specific captions
    and optionally auto-schedule at optimal times.

    Args:
        payload: Product data, target platforms, auto-schedule flag, and tone.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ProductToPostResponse with generated posts and platforms count.

    Raises:
        HTTPException 400: If no connected account is found.
    """
    # Use a dummy account_id for now (in production, we'd look up connected accounts)
    # For each platform, find the user's connected account or use a default
    from sqlalchemy import select
    from app.models.social_account import SocialAccount

    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.user_id == current_user.id,
            SocialAccount.is_connected.is_(True),
        ).limit(1)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No connected social account found. Connect an account first.",
        )

    posts = await product_to_posts(
        db=db,
        user_id=current_user.id,
        account_id=account.id,
        product_data=payload.product_data,
        platforms=payload.platforms,
        auto_schedule=payload.auto_schedule,
        tone=payload.tone,
    )

    return ProductToPostResponse(
        posts=posts,
        platforms_processed=len(payload.platforms),
    )


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new post",
)
async def create_new_post(
    payload: PostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new social media post.

    Enforces the plan's monthly post limit (max_items). If scheduled_for
    is provided, the post is created with status "scheduled"; otherwise
    it starts as "draft".

    Args:
        payload: Post creation data (content, media, hashtags, platform, schedule).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created PostResponse.

    Raises:
        HTTPException 403: If monthly post limit is reached.
    """
    try:
        post = await create_post(
            db=db,
            user=current_user,
            account_id=payload.account_id,
            content=payload.content,
            platform=payload.platform,
            media_urls=payload.media_urls,
            hashtags=payload.hashtags,
            scheduled_for=payload.scheduled_for,
        )
        return post
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get(
    "",
    response_model=PostListResponse,
    summary="List posts with pagination",
)
async def list_user_posts(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: PostStatus | None = Query(None, alias="status", description="Filter by status"),
    platform: str | None = Query(None, description="Filter by platform"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all posts with optional filtering and pagination.

    Supports filtering by status (draft, scheduled, posted, failed) and
    platform (instagram, facebook, tiktok, twitter, pinterest).

    Args:
        page: Page number (1-indexed).
        per_page: Items per page (max 100).
        status_filter: Optional status filter.
        platform: Optional platform filter.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PostListResponse with items, total, page, per_page.
    """
    posts, total = await list_posts(
        db=db,
        user=current_user,
        page=page,
        per_page=per_page,
        status=status_filter,
        platform=platform,
    )
    return PostListResponse(items=posts, total=total, page=page, per_page=per_page)


@router.get(
    "/calendar",
    response_model=CalendarView,
    summary="Get calendar view of scheduled posts",
)
async def get_calendar(
    start_date: date = Query(..., description="Calendar start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Calendar end date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get posts grouped by date for the calendar view.

    Returns posts within the specified date range, grouped by their
    scheduled_for date. Includes suggested posting times per platform.

    Args:
        start_date: Start of the date range (inclusive).
        end_date: End of the date range (inclusive).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CalendarView with days (including suggested times) and total_posts.
    """
    grouped = await get_calendar_posts(
        db=db, user=current_user, start_date=start_date, end_date=end_date
    )

    # Build suggested times for all platforms
    all_platforms = ["instagram", "facebook", "tiktok", "twitter", "pinterest"]
    suggested_times = []
    for plat in all_platforms:
        for t in get_best_times(plat):
            suggested_times.append(
                SuggestedTime(platform=plat, time=t["time"], label=t["label"])
            )

    days = [
        CalendarDay(date=d, posts=posts, suggested_times=suggested_times)
        for d, posts in sorted(grouped.items())
    ]
    total_posts = sum(len(d.posts) for d in days)

    return CalendarView(days=days, total_posts=total_posts)


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Get a single post",
)
async def get_single_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single post by ID.

    Args:
        post_id: UUID of the post to retrieve.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The PostResponse.

    Raises:
        HTTPException 404: If the post is not found or doesn't belong to the user.
    """
    post = await get_post(db=db, user=current_user, post_id=post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
    summary="Update a post",
)
async def update_existing_post(
    post_id: uuid.UUID,
    payload: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing post (partial update).

    Only draft and scheduled posts can be updated. Posted or failed posts
    are immutable.

    Args:
        post_id: UUID of the post to update.
        payload: Partial update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated PostResponse.

    Raises:
        HTTPException 404: If post not found.
        HTTPException 400: If post cannot be updated (already posted/failed).
    """
    try:
        # Build kwargs, using Ellipsis sentinel for unset scheduled_for
        kwargs: dict = {}
        if payload.content is not None:
            kwargs["content"] = payload.content
        if payload.media_urls is not None:
            kwargs["media_urls"] = payload.media_urls
        if payload.hashtags is not None:
            kwargs["hashtags"] = payload.hashtags
        # scheduled_for: always pass through (None means "clear schedule")
        if payload.scheduled_for is not None:
            kwargs["scheduled_for"] = payload.scheduled_for

        post = await update_post(db=db, user=current_user, post_id=post_id, **kwargs)
        return post
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a post",
)
async def delete_existing_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a post permanently.

    Only draft and scheduled posts can be deleted. Published posts are
    preserved for analytics history.

    Args:
        post_id: UUID of the post to delete.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If post not found.
        HTTPException 400: If post cannot be deleted (already published).
    """
    try:
        await delete_post(db=db, user=current_user, post_id=post_id)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)


@router.post(
    "/{post_id}/schedule",
    response_model=PostResponse,
    summary="Schedule a post for publication",
)
async def schedule_existing_post(
    post_id: uuid.UUID,
    payload: PostSchedule,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Schedule a draft post for future publication.

    Sets the post status to "scheduled" and assigns the scheduled_for time.
    The Celery worker will publish the post at the scheduled time.

    Args:
        post_id: UUID of the post to schedule.
        payload: Schedule time.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated PostResponse with status=scheduled.

    Raises:
        HTTPException 404: If post not found.
        HTTPException 400: If post cannot be scheduled or time is in the past.
    """
    try:
        post = await schedule_post(
            db=db,
            user=current_user,
            post_id=post_id,
            scheduled_for=payload.scheduled_for,
        )
        return post
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)


@router.post(
    "/{post_id}/metrics",
    response_model=PostMetricsResponse,
    summary="Record metrics for a post",
)
async def record_post_metrics(
    post_id: uuid.UUID,
    payload: MetricsRecordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Record engagement metrics for a published post.

    Creates or updates a PostMetrics record. Computes the engagement rate
    automatically from the provided metrics data.

    Args:
        post_id: UUID of the post.
        payload: Metrics data (impressions, reach, likes, comments, shares, clicks).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PostMetricsResponse with recorded metrics and engagement rate.

    Raises:
        HTTPException 404: If the post is not found.
    """
    try:
        metrics = await record_metrics(
            db=db,
            post_id=post_id,
            metrics_data=payload.model_dump(),
        )

        engagement_rate = 0.0
        if metrics.impressions > 0:
            engagement_rate = round(
                (metrics.likes + metrics.comments + metrics.shares)
                / metrics.impressions * 100,
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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
