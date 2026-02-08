"""Notifications API router.

Provides endpoints for managing user notifications. Notifications are
user-scoped (not store-scoped) and include order updates, system alerts,
team invitations, and other events.

**For Developers:**
    The router is prefixed with ``/notifications`` (full path:
    ``/api/v1/notifications/...``). All endpoints require authentication.
    Notifications are scoped to the authenticated user, not a specific store.
    Service functions in ``notification_service`` handle all business logic.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - GET list supports ``?page=``, ``?per_page=``, ``?unread_only=`` params.
    - Mark-read accepts a list of notification IDs.
    - Mark-all-read marks every unread notification for the user.
    - DELETE returns 204 with no content.

**For End Users:**
    - View notifications about orders, team invites, and system events.
    - Mark notifications as read individually or all at once.
    - See your unread notification count for badge display.
    - Delete notifications you no longer need.
"""

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.notification import (
    MarkReadRequest,
    NotificationResponse,
    PaginatedNotificationResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Local response schemas (not in app.schemas.notification)
# ---------------------------------------------------------------------------


class MarkReadResponse(BaseModel):
    """Response after marking notifications as read.

    Attributes:
        marked: Number of notifications marked as read.
        message: Human-readable confirmation message.
    """

    marked: int
    message: str


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedNotificationResponse)
async def list_notifications_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedNotificationResponse:
    """List notifications for the authenticated user.

    Returns notifications ordered by creation date (newest first).
    Optionally filter to show only unread notifications.

    Args:
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        unread_only: If true, only return unread notifications.
        current_user: The authenticated user.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedNotificationResponse with items and pagination metadata.
    """
    from app.services import notification_service

    try:
        notifications, total = await notification_service.list_notifications(
            db,
            user_id=current_user.id,
            page=page,
            per_page=per_page,
            unread_only=unread_only,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedNotificationResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    """Get the count of unread notifications for the authenticated user.

    Used by the frontend to display a notification badge.

    Args:
        current_user: The authenticated user.
        db: Async database session injected by FastAPI.

    Returns:
        UnreadCountResponse with the unread notification count.
    """
    from app.services import notification_service

    count = await notification_service.get_unread_count(
        db, user_id=current_user.id
    )
    return UnreadCountResponse(count=count)


@router.post("/mark-read", response_model=MarkReadResponse)
async def mark_notifications_read_endpoint(
    request: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarkReadResponse:
    """Mark specific notifications as read.

    Accepts a list of notification IDs to mark as read. Only notifications
    belonging to the authenticated user are updated.

    Args:
        request: List of notification UUIDs to mark as read.
        current_user: The authenticated user.
        db: Async database session injected by FastAPI.

    Returns:
        MarkReadResponse with the count of marked notifications.
    """
    from app.services import notification_service

    marked = await notification_service.mark_as_read(
        db,
        user_id=current_user.id,
        notification_ids=request.notification_ids,
    )
    return MarkReadResponse(
        marked=marked,
        message=f"Marked {marked} notification(s) as read",
    )


@router.post("/mark-all-read", response_model=MarkReadResponse)
async def mark_all_notifications_read_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarkReadResponse:
    """Mark all notifications as read for the authenticated user.

    Bulk operation that marks every unread notification as read.

    Args:
        current_user: The authenticated user.
        db: Async database session injected by FastAPI.

    Returns:
        MarkReadResponse with the count of marked notifications.
    """
    from app.services import notification_service

    marked = await notification_service.mark_all_as_read(
        db, user_id=current_user.id
    )
    return MarkReadResponse(
        marked=marked,
        message=f"Marked {marked} notification(s) as read",
    )


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_endpoint(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a notification.

    Only the notification owner can delete their notifications.

    Args:
        notification_id: The UUID of the notification to delete.
        current_user: The authenticated user.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the notification is not found.
    """
    from app.services import notification_service

    try:
        await notification_service.delete_notification(
            db, user_id=current_user.id, notification_id=notification_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
