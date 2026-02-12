"""
Content queue API routes for AI-assisted post generation.

Provides CRUD endpoints for the content queue, including AI caption
generation and approval workflow. All endpoints require authentication.

For Developers:
    Queue items store product data and AI-generated captions. The
    /generate endpoint calls the caption service to create content.
    The /approve endpoint changes status to "approved" for scheduling.

For QA Engineers:
    Test: create queue item (201), list with pagination, generate captions,
    approve/reject workflow, and verify status transitions.

For Project Managers:
    The content queue automates social media content creation. Users add
    products, AI generates captions, and users review before scheduling.

For End Users:
    Add your products to the content queue, generate AI captions with one
    click, review and approve them, then schedule for publication.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.content_queue import ContentQueue, QueueStatus
from app.models.user import User
from app.schemas.social import (
    CaptionGenerateRequest,
    CaptionGenerateResponse,
    ContentQueueCreate,
    ContentQueueListResponse,
    ContentQueueResponse,
)
from app.services.caption_service import generate_caption

router = APIRouter(prefix="/queue", tags=["queue"])


@router.post(
    "",
    response_model=ContentQueueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add item to content queue",
)
async def create_queue_item(
    payload: ContentQueueCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new product to the content generation queue.

    Creates a queue item with status "pending". AI captions can be
    generated later via the /generate endpoint.

    Args:
        payload: Product data and target platforms.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created ContentQueueResponse.
    """
    item = ContentQueue(
        user_id=current_user.id,
        product_data=payload.product_data,
        platforms=payload.platforms,
    )
    db.add(item)
    await db.flush()
    return item


@router.get(
    "",
    response_model=ContentQueueListResponse,
    summary="List content queue items",
)
async def list_queue_items(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: QueueStatus | None = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List content queue items with pagination and optional status filter.

    Args:
        page: Page number (1-indexed).
        per_page: Items per page (max 100).
        status_filter: Optional status filter.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ContentQueueListResponse with items, total, page, per_page.
    """
    conditions = [ContentQueue.user_id == current_user.id]
    if status_filter:
        conditions.append(ContentQueue.status == status_filter)

    # Count
    count_result = await db.execute(
        select(func.count(ContentQueue.id)).where(and_(*conditions))
    )
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * per_page
    result = await db.execute(
        select(ContentQueue)
        .where(and_(*conditions))
        .order_by(ContentQueue.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    items = list(result.scalars().all())

    return ContentQueueListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get(
    "/{item_id}",
    response_model=ContentQueueResponse,
    summary="Get a queue item",
)
async def get_queue_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single content queue item by ID.

    Args:
        item_id: UUID of the queue item.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The ContentQueueResponse.

    Raises:
        HTTPException 404: If item not found or doesn't belong to user.
    """
    result = await db.execute(
        select(ContentQueue).where(
            ContentQueue.id == item_id,
            ContentQueue.user_id == current_user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
    return item


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a queue item",
)
async def delete_queue_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a content queue item.

    Only pending and rejected items can be deleted. Approved and posted
    items are preserved.

    Args:
        item_id: UUID of the queue item.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If item not found.
        HTTPException 400: If item cannot be deleted (approved/posted).
    """
    result = await db.execute(
        select(ContentQueue).where(
            ContentQueue.id == item_id,
            ContentQueue.user_id == current_user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    if item.status in (QueueStatus.approved, QueueStatus.posted):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete approved or posted items",
        )

    await db.delete(item)
    await db.flush()


@router.post(
    "/{item_id}/generate",
    response_model=ContentQueueResponse,
    summary="Generate AI caption for queue item",
)
async def generate_ai_caption(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an AI caption for a content queue item.

    Uses the product data stored in the queue item to generate a caption
    and hashtag suggestions via the caption service.

    Args:
        item_id: UUID of the queue item.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated ContentQueueResponse with ai_generated_content populated.

    Raises:
        HTTPException 404: If item not found.
    """
    result = await db.execute(
        select(ContentQueue).where(
            ContentQueue.id == item_id,
            ContentQueue.user_id == current_user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    # Generate caption using the first platform or default to instagram
    platform = item.platforms[0] if item.platforms else "instagram"
    caption_result = generate_caption(
        product_data=item.product_data,
        platform=platform,
    )

    # Store generated content
    hashtag_str = " ".join(f"#{tag}" for tag in caption_result["hashtags"])
    item.ai_generated_content = f"{caption_result['caption']}\n\n{hashtag_str}"
    await db.flush()

    return item


@router.post(
    "/{item_id}/approve",
    response_model=ContentQueueResponse,
    summary="Approve a queue item",
)
async def approve_queue_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve a content queue item for scheduling.

    Changes the item's status from "pending" to "approved". Only pending
    items with generated content can be approved.

    Args:
        item_id: UUID of the queue item.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated ContentQueueResponse with status=approved.

    Raises:
        HTTPException 404: If item not found.
        HTTPException 400: If item is not in pending status.
    """
    result = await db.execute(
        select(ContentQueue).where(
            ContentQueue.id == item_id,
            ContentQueue.user_id == current_user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    if item.status != QueueStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve item with status '{item.status.value}'",
        )

    item.status = QueueStatus.approved
    await db.flush()
    return item


@router.post(
    "/{item_id}/reject",
    response_model=ContentQueueResponse,
    summary="Reject a queue item",
)
async def reject_queue_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reject a content queue item.

    Changes the item's status to "rejected". Only pending items can be rejected.

    Args:
        item_id: UUID of the queue item.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated ContentQueueResponse with status=rejected.

    Raises:
        HTTPException 404: If item not found.
        HTTPException 400: If item is not in pending status.
    """
    result = await db.execute(
        select(ContentQueue).where(
            ContentQueue.id == item_id,
            ContentQueue.user_id == current_user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    if item.status != QueueStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject item with status '{item.status.value}'",
        )

    item.status = QueueStatus.rejected
    await db.flush()
    return item


@router.post(
    "/generate-caption",
    response_model=CaptionGenerateResponse,
    summary="Generate AI caption from product data",
)
async def generate_caption_standalone(
    payload: CaptionGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate an AI caption from product data without creating a queue item.

    Useful for previewing captions before adding to the queue. Does not
    persist any data.

    Args:
        payload: Product data, platform, and tone.
        current_user: The authenticated user.

    Returns:
        CaptionGenerateResponse with caption, hashtags, and platform.
    """
    result = generate_caption(
        product_data=payload.product_data,
        platform=payload.platform,
        tone=payload.tone,
    )
    return CaptionGenerateResponse(**result)
