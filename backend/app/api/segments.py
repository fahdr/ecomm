"""Customer Segments API router.

Provides CRUD endpoints for managing customer segments. Store owners can
group customers into segments for targeted marketing, analytics, and
personalized experiences.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/segments/...``
    (full path: ``/api/v1/stores/{store_id}/segments/...``).
    The ``get_current_user`` dependency is used for authentication.
    Service functions in ``segment_service`` handle all business logic.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - POST create returns 201 with the segment data.
    - DELETE returns 204 with no content.
    - Adding a customer to a segment is idempotent.
    - Segments can be rule-based (auto) or manual.

**For End Users:**
    - Create customer segments for targeted marketing campaigns.
    - Manually add or remove customers from segments.
    - Use segments to filter analytics and send targeted emails.
"""

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.segment import (
    AddCustomersToSegmentRequest,
    CreateSegmentRequest,
    PaginatedSegmentResponse,
    SegmentResponse,
    UpdateSegmentRequest,
)

router = APIRouter(prefix="/stores/{store_id}/segments", tags=["segments"])


# ---------------------------------------------------------------------------
# Local schemas for segment customer endpoints (not in app.schemas.segment)
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SegmentCustomerResponse(BaseModel):
    """Response schema for a customer in a segment.

    Attributes:
        customer_id: The customer's UUID.
        email: Customer email address.
        name: Customer display name.
        added_at: When the customer was added to the segment.
    """

    customer_id: uuid.UUID
    email: str
    name: Optional[str] = None
    added_at: datetime

    model_config = {"from_attributes": True}


class PaginatedSegmentCustomerResponse(BaseModel):
    """Paginated list of customers in a segment.

    Attributes:
        items: List of segment customer records.
        total: Total number of customers.
        page: Current page number.
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[SegmentCustomerResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.post("", response_model=SegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_segment_endpoint(
    store_id: uuid.UUID,
    request: CreateSegmentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SegmentResponse:
    """Create a new customer segment for a store.

    Creates a segment that can be populated manually or automatically
    based on rules. Auto segments evaluate rules to include matching
    customers.

    Args:
        store_id: The UUID of the store.
        request: Segment creation payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        SegmentResponse with the newly created segment data.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
        HTTPException 400: If the segment name already exists in this store.
    """
    from app.services import segment_service

    try:
        segment = await segment_service.create_segment(
            db,
            store_id=store_id,
            user_id=current_user.id,
            **request.model_dump(),
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already exists" in detail
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return SegmentResponse.model_validate(segment)


@router.get("", response_model=PaginatedSegmentResponse)
async def list_segments_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedSegmentResponse:
    """List customer segments for a store with pagination.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedSegmentResponse with items, total, and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import segment_service

    try:
        segments, total = await segment_service.list_segments(
            db,
            store_id=store_id,
            user_id=current_user.id,
            page=page,
            per_page=per_page,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedSegmentResponse(
        items=[SegmentResponse.model_validate(s) for s in segments],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{segment_id}", response_model=SegmentResponse)
async def get_segment_endpoint(
    store_id: uuid.UUID,
    segment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SegmentResponse:
    """Retrieve a single segment by ID.

    Args:
        store_id: The UUID of the store.
        segment_id: The UUID of the segment to retrieve.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        SegmentResponse with the segment data.

    Raises:
        HTTPException 404: If the store or segment is not found.
    """
    from app.services import segment_service

    try:
        segment = await segment_service.get_segment(
            db, store_id=store_id, user_id=current_user.id, segment_id=segment_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return SegmentResponse.model_validate(segment)


@router.patch("/{segment_id}", response_model=SegmentResponse)
async def update_segment_endpoint(
    store_id: uuid.UUID,
    segment_id: uuid.UUID,
    request: UpdateSegmentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SegmentResponse:
    """Update a segment's fields (partial update).

    Only provided fields are updated.

    Args:
        store_id: The UUID of the store.
        segment_id: The UUID of the segment to update.
        request: Partial update payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        SegmentResponse with the updated segment data.

    Raises:
        HTTPException 404: If the store or segment is not found.
    """
    from app.services import segment_service

    try:
        segment = await segment_service.update_segment(
            db,
            store_id=store_id,
            user_id=current_user.id,
            segment_id=segment_id,
            **request.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return SegmentResponse.model_validate(segment)


@router.delete("/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment_endpoint(
    store_id: uuid.UUID,
    segment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a customer segment and all its customer associations.

    Args:
        store_id: The UUID of the store.
        segment_id: The UUID of the segment to delete.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the store or segment is not found.
    """
    from app.services import segment_service

    try:
        await segment_service.delete_segment(
            db, store_id=store_id, user_id=current_user.id, segment_id=segment_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{segment_id}/customers",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def add_customers_to_segment_endpoint(
    store_id: uuid.UUID,
    segment_id: uuid.UUID,
    request: AddCustomersToSegmentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add customers to a segment.

    This operation is idempotent: customers already in the segment are
    silently skipped.

    Args:
        store_id: The UUID of the store.
        segment_id: The UUID of the segment.
        request: List of customer UUIDs to add.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        A dict with a confirmation message and count of added customers.

    Raises:
        HTTPException 404: If the store, segment, or any customer is not found.
    """
    from app.services import segment_service

    try:
        added = await segment_service.add_customers_to_segment(
            db,
            store_id=store_id,
            user_id=current_user.id,
            segment_id=segment_id,
            customer_ids=request.customer_ids,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return {
        "segment_id": str(segment_id),
        "added": added,
        "message": f"Added {added} customer(s) to segment",
    }


@router.delete(
    "/{segment_id}/customers/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_customer_from_segment_endpoint(
    store_id: uuid.UUID,
    segment_id: uuid.UUID,
    customer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a customer from a segment.

    Args:
        store_id: The UUID of the store.
        segment_id: The UUID of the segment.
        customer_id: The UUID of the customer to remove.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the association is not found.
    """
    from app.services import segment_service

    try:
        await segment_service.remove_customer_from_segment(
            db,
            store_id=store_id,
            user_id=current_user.id,
            segment_id=segment_id,
            customer_id=customer_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{segment_id}/customers",
    response_model=PaginatedSegmentCustomerResponse,
)
async def list_segment_customers_endpoint(
    store_id: uuid.UUID,
    segment_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedSegmentCustomerResponse:
    """List customers in a segment with pagination.

    Args:
        store_id: The UUID of the store.
        segment_id: The UUID of the segment.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedSegmentCustomerResponse with customers and pagination metadata.

    Raises:
        HTTPException 404: If the store or segment is not found.
    """
    from app.services import segment_service

    try:
        customers, total = await segment_service.get_segment_customers(
            db,
            store_id=store_id,
            user_id=current_user.id,
            segment_id=segment_id,
            page=page,
            per_page=per_page,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedSegmentCustomerResponse(
        items=[SegmentCustomerResponse.model_validate(c) for c in customers],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
