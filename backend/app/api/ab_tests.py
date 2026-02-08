"""A/B Tests API router.

Provides endpoints for managing A/B tests on store pages and components.
Store owners can create experiments with multiple variants, track
conversions, and analyze results to optimize their storefront.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/ab-tests/...``
    (full path: ``/api/v1/stores/{store_id}/ab-tests/...``).
    The ``get_current_user`` dependency is used for authentication.
    Service functions in ``ab_test_service`` handle experiment logic.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - POST create returns 201 with the test configuration.
    - Test statuses: ``draft``, ``running``, ``paused``, ``completed``.
    - Variant assignment uses consistent hashing by visitor ID.
    - Events endpoint records conversions and page views.
    - GET with results includes statistical significance.
    - DELETE returns 204 with no content.

**For End Users:**
    - Create A/B tests to compare different page designs.
    - Track visitor behavior across test variants.
    - Analyze results to determine the winning variant.
    - Implement data-driven optimizations to your storefront.
"""

import math
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.ab_test import (
    ABTestResponse,
    CreateABTestRequest,
    PaginatedABTestResponse,
    RecordEventRequest,
    UpdateABTestRequest,
)

router = APIRouter(prefix="/stores/{store_id}/ab-tests", tags=["ab-tests"])


# ---------------------------------------------------------------------------
# Additional response schemas used only by the API layer
# ---------------------------------------------------------------------------


class RecordEventResponse(BaseModel):
    """Response after recording an event.

    Attributes:
        recorded: Whether the event was successfully recorded.
        message: Human-readable confirmation message.
    """

    recorded: bool
    message: str


class VariantAssignmentResponse(BaseModel):
    """Response with the assigned variant for a visitor.

    Attributes:
        test_id: The A/B test UUID.
        variant_name: The assigned variant name.
        variant_config: The variant's configuration.
    """

    test_id: uuid.UUID
    variant_name: str
    variant_config: Optional[dict] = None


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.post("", response_model=ABTestResponse, status_code=status.HTTP_201_CREATED)
async def create_ab_test_endpoint(
    store_id: uuid.UUID,
    request: CreateABTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ABTestResponse:
    """Create a new A/B test for a store.

    Defines an experiment with two or more variants. The test starts
    in ``draft`` status and must be explicitly activated. Variant
    weights must sum to 100.

    Args:
        store_id: The UUID of the store.
        request: A/B test creation payload with variants.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        ABTestResponse with the newly created test configuration.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
        HTTPException 400: If variant weights don't sum to 100 or names conflict.
    """
    from app.services import ab_test_service

    try:
        # Convert variant inputs to dicts for the service
        variants_data = [v.model_dump() for v in request.variants]

        test = await ab_test_service.create_test(
            db,
            store_id=store_id,
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            metric=request.metric,
            variants=variants_data,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "weight" in detail.lower()
            or "variant" in detail.lower()
            or "invalid" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return ABTestResponse.model_validate(test)


@router.get("", response_model=PaginatedABTestResponse)
async def list_ab_tests_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedABTestResponse:
    """List A/B tests for a store with pagination.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedABTestResponse with tests and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import ab_test_service

    try:
        tests, total = await ab_test_service.list_tests(
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

    return PaginatedABTestResponse(
        items=[ABTestResponse.model_validate(t) for t in tests],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{test_id}", response_model=ABTestResponse)
async def get_ab_test_endpoint(
    store_id: uuid.UUID,
    test_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ABTestResponse:
    """Retrieve a single A/B test with its results.

    Returns the test configuration along with per-variant statistical
    results including conversion rates and confidence levels.

    Args:
        store_id: The UUID of the store.
        test_id: The UUID of the A/B test.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        ABTestResponse with test config and statistical results.

    Raises:
        HTTPException 404: If the store or test is not found.
    """
    from app.services import ab_test_service

    try:
        test = await ab_test_service.get_test(
            db, store_id=store_id, user_id=current_user.id, test_id=test_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return ABTestResponse.model_validate(test)


@router.patch("/{test_id}", response_model=ABTestResponse)
async def update_ab_test_endpoint(
    store_id: uuid.UUID,
    test_id: uuid.UUID,
    request: UpdateABTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ABTestResponse:
    """Update an A/B test (partial update).

    Use this to change the test name, description, or status.
    Changing status to ``running`` starts the test; ``completed``
    ends it and locks the results.

    Args:
        store_id: The UUID of the store.
        test_id: The UUID of the test to update.
        request: Partial update payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        ABTestResponse with the updated test data.

    Raises:
        HTTPException 404: If the store or test is not found.
        HTTPException 400: If the status transition is invalid.
    """
    from app.services import ab_test_service

    try:
        test = await ab_test_service.update_test(
            db,
            store_id=store_id,
            user_id=current_user.id,
            test_id=test_id,
            **request.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "invalid" in detail.lower() or "cannot" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return ABTestResponse.model_validate(test)


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ab_test_endpoint(
    store_id: uuid.UUID,
    test_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete an A/B test and all its event data.

    Running tests must be stopped before deletion.

    Args:
        store_id: The UUID of the store.
        test_id: The UUID of the test to delete.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the store or test is not found.
        HTTPException 400: If the test is currently running.
    """
    from app.services import ab_test_service

    try:
        await ab_test_service.delete_test(
            db, store_id=store_id, user_id=current_user.id, test_id=test_id
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "running" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{test_id}/events", response_model=RecordEventResponse)
async def record_event_endpoint(
    store_id: uuid.UUID,
    test_id: uuid.UUID,
    request: RecordEventRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecordEventResponse:
    """Record an A/B test event (pageview, click, purchase).

    Tracks visitor interactions with test variants for statistical
    analysis. Events are deduplicated by visitor_id + event_type
    per variant.

    Args:
        store_id: The UUID of the store.
        test_id: The UUID of the A/B test.
        request: Event recording payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        RecordEventResponse confirming the event was recorded.

    Raises:
        HTTPException 404: If the store or test is not found.
        HTTPException 400: If the test is not running or variant is invalid.
    """
    from app.services import ab_test_service

    try:
        # Verify store ownership
        await ab_test_service.get_test(
            db, store_id=store_id, user_id=current_user.id, test_id=test_id
        )

        # Service takes variant_id, event_type, optional revenue
        await ab_test_service.record_event(
            db,
            variant_id=request.variant_id,
            event_type=request.event_type,
            revenue=request.revenue,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "not running" in detail.lower() or "invalid" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return RecordEventResponse(recorded=True, message="Event recorded successfully")


@router.get("/{test_id}/variant", response_model=VariantAssignmentResponse)
async def get_variant_assignment_endpoint(
    store_id: uuid.UUID,
    test_id: uuid.UUID,
    visitor_id: str = Query(..., min_length=1, description="Unique visitor identifier"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VariantAssignmentResponse:
    """Get the assigned variant for a visitor.

    Uses consistent hashing to deterministically assign visitors to
    variants based on their visitor_id. The same visitor always gets
    the same variant for a given test.

    Args:
        store_id: The UUID of the store.
        test_id: The UUID of the A/B test.
        visitor_id: Unique identifier for the visitor (cookie, fingerprint).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        VariantAssignmentResponse with the assigned variant name and config.

    Raises:
        HTTPException 404: If the store or test is not found.
        HTTPException 400: If the test is not running.
    """
    from app.services import ab_test_service

    try:
        # Verify store ownership
        await ab_test_service.get_test(
            db, store_id=store_id, user_id=current_user.id, test_id=test_id
        )

        # Service returns an ABTestVariant ORM instance
        variant = await ab_test_service.get_assigned_variant(
            db,
            test_id=test_id,
            visitor_id=visitor_id,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "not running" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return VariantAssignmentResponse(
        test_id=test_id,
        variant_name=variant.name,
        variant_config=variant.config,
    )
