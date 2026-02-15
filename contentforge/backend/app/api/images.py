"""
Image management API endpoints.

Provides read and delete operations for processed product images.
Images are created as part of content generation jobs and can be
viewed and managed independently through these endpoints.

For Developers:
    Image records are associated with generation jobs. The ownership
    check joins through GenerationJob to verify the requesting user
    owns the parent job. Images are paginated using the standard
    `?page=1&per_page=20` pattern.

For QA Engineers:
    Test pagination with various page sizes.
    Verify ownership checks — user A cannot view user B's images.
    Test deletion — verify the image record is removed.
    Test with no images — should return empty list, not error.

For Project Managers:
    The Images page gives users a visual gallery of all their processed
    product images. It shows original vs optimized size savings and
    supports bulk download and deletion.

For End Users:
    View all your processed product images in one place. Each image
    shows the original and optimized file sizes, format, and dimensions.
    Delete images you no longer need to keep your workspace clean.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.content import ImageJobResponse, PaginatedImages
from app.services.image_service import delete_image, get_image, get_images

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/", response_model=PaginatedImages)
async def list_images(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List the current user's processed images with pagination.

    Images are ordered by creation date (newest first). Includes images
    from all generation jobs owned by the user.

    Args:
        page: Page number (1-indexed, default 1).
        per_page: Number of items per page (default 20, max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PaginatedImages with items, total, page, per_page.
    """
    result = await get_images(db, current_user.id, page, per_page)
    return result


@router.get("/{image_id}", response_model=ImageJobResponse)
async def get_image_detail(
    image_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details for a single processed image.

    Args:
        image_id: The image job UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ImageJobResponse with image details.

    Raises:
        HTTPException 404: If the image is not found or not owned by the user.
    """
    image = await get_image(db, image_id, current_user.id)
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )
    return image


@router.delete("/{image_id}", status_code=204)
async def delete_image_record(
    image_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a processed image record.

    Only the owning user can delete their images.

    Args:
        image_id: The image job UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If the image is not found or not owned by the user.
    """
    deleted = await delete_image(db, image_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )
