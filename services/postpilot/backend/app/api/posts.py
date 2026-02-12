"""
Post management API routes.

Provides CRUD endpoints for social media posts, scheduling, and calendar
views. All endpoints require authentication via JWT Bearer token.

For Developers:
    Post creation enforces plan limits (max_items = posts/month). The
    calendar endpoint accepts start_date/end_date query parameters and
    returns posts grouped by date. Pagination uses page/per_page params.

For QA Engineers:
    Test: create post (201), list with pagination, update draft, schedule,
    delete draft, calendar view with date range, plan limit enforcement (403).

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

from app.api.deps import get_current_user
from app.database import get_db
from app.models.post import PostStatus
from app.models.user import User
from app.schemas.social import (
    CalendarDay,
    CalendarView,
    PostCreate,
    PostListResponse,
    PostResponse,
    PostSchedule,
    PostUpdate,
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

router = APIRouter(prefix="/posts", tags=["posts"])


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
    platform (instagram, facebook, tiktok).

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
    scheduled_for date.

    Args:
        start_date: Start of the date range (inclusive).
        end_date: End of the date range (inclusive).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        CalendarView with days and total_posts.
    """
    grouped = await get_calendar_posts(
        db=db, user=current_user, start_date=start_date, end_date=end_date
    )

    days = [CalendarDay(date=d, posts=posts) for d, posts in sorted(grouped.items())]
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
