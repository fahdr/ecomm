"""
Alert notification API endpoints.

Provides read-only access to CompetitorAlert notifications and the ability
to mark them as read. These alerts are auto-generated from catalog diffs.

For Developers:
    GET /api/v1/alerts — list alerts with optional filters (is_read, alert_type).
    PATCH /api/v1/alerts/{id}/read — mark a single alert as read.
    PATCH /api/v1/alerts/read-all — mark all alerts as read.

For QA Engineers:
    Test alert listing with filters, pagination, and mark-as-read.
    Verify that unread counts update correctly. Ensure authorization
    isolation (users only see their own alerts).

For Project Managers:
    The alerts feed powers the notification panel in the dashboard.
    Users see real-time updates about competitor changes.

For End Users:
    Check your alerts to see recent competitor changes. Mark them as
    read to keep your notification feed clean.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_current_user
from app.models.competitor_alert import CompetitorAlert
from app.models.user import User

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ── Schemas ────────────────────────────────────────────────────────


class CompetitorAlertResponse(BaseModel):
    """
    Response schema for a competitor alert notification.

    Attributes:
        id: Unique identifier.
        competitor_id: Related competitor ID (optional).
        alert_type: Type of alert event.
        severity: Alert severity level.
        message: Human-readable alert message.
        data: Contextual data dict.
        is_read: Whether the alert has been read.
        created_at: When the alert was generated.
    """

    id: uuid.UUID
    competitor_id: uuid.UUID | None
    alert_type: str
    severity: str
    message: str
    data: dict
    is_read: bool
    created_at: str

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """
    Paginated list of alerts with unread count.

    Attributes:
        items: List of alert records.
        total: Total number of matching alerts.
        unread_count: Number of unread alerts.
        page: Current page number.
        per_page: Items per page.
    """

    items: list[CompetitorAlertResponse]
    total: int
    unread_count: int
    page: int
    per_page: int


class MarkReadResponse(BaseModel):
    """
    Response after marking alerts as read.

    Attributes:
        message: Status message.
        updated_count: Number of alerts marked as read.
    """

    message: str
    updated_count: int


# ── Endpoints ──────────────────────────────────────────────────────


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    is_read: bool | None = Query(None, description="Filter by read status"),
    alert_type: str | None = Query(None, description="Filter by alert type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List alert notifications for the authenticated user.

    Supports filtering by read status and alert type. Returns alerts
    ordered by creation time (newest first) with an unread count.

    Args:
        page: Page number (1-based).
        per_page: Items per page (max 100).
        is_read: Optional filter for read/unread alerts.
        alert_type: Optional filter by alert type.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        AlertListResponse with paginated alerts and unread count.
    """
    # Build filter conditions
    conditions = [CompetitorAlert.user_id == current_user.id]
    if is_read is not None:
        conditions.append(CompetitorAlert.is_read == is_read)
    if alert_type:
        conditions.append(CompetitorAlert.alert_type == alert_type)

    # Count total matching
    count_result = await db.execute(
        select(func.count(CompetitorAlert.id)).where(*conditions)
    )
    total = count_result.scalar_one()

    # Count unread (always show total unread regardless of filters)
    unread_result = await db.execute(
        select(func.count(CompetitorAlert.id)).where(
            CompetitorAlert.user_id == current_user.id,
            CompetitorAlert.is_read == False,  # noqa: E712
        )
    )
    unread_count = unread_result.scalar_one()

    # Fetch page
    offset = (page - 1) * per_page
    result = await db.execute(
        select(CompetitorAlert)
        .where(*conditions)
        .order_by(CompetitorAlert.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    alerts = result.scalars().all()

    items = [
        CompetitorAlertResponse(
            id=a.id,
            competitor_id=a.competitor_id,
            alert_type=a.alert_type,
            severity=a.severity,
            message=a.message,
            data=a.data,
            is_read=a.is_read,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in alerts
    ]

    return AlertListResponse(
        items=items,
        total=total,
        unread_count=unread_count,
        page=page,
        per_page=per_page,
    )


@router.patch("/{alert_id}/read", response_model=MarkReadResponse)
async def mark_alert_read(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a single alert as read.

    Args:
        alert_id: The alert's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        MarkReadResponse with status message.

    Raises:
        HTTPException 400: If the alert ID is not a valid UUID.
        HTTPException 404: If the alert is not found or not owned by user.
    """
    try:
        aid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID")

    result = await db.execute(
        select(CompetitorAlert).where(
            CompetitorAlert.id == aid,
            CompetitorAlert.user_id == current_user.id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    alert.is_read = True
    await db.flush()

    return MarkReadResponse(message="Alert marked as read", updated_count=1)


@router.patch("/read-all", response_model=MarkReadResponse)
async def mark_all_alerts_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark all of the user's alerts as read.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        MarkReadResponse with the number of alerts updated.
    """
    result = await db.execute(
        update(CompetitorAlert)
        .where(
            CompetitorAlert.user_id == current_user.id,
            CompetitorAlert.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    count = result.rowcount

    return MarkReadResponse(
        message=f"Marked {count} alert(s) as read",
        updated_count=count,
    )
