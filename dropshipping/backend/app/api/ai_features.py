"""
AI features API router for the Dropshipping platform.

Exposes endpoints for AI-powered product description generation and
pricing optimization. All endpoints require JWT authentication and
store ownership validation.

For Developers:
    Mount this router in ``main.py`` with prefix ``/api/v1``.
    Uses ``get_current_user`` from ``app.api.deps`` for authentication.
    Store ownership is validated within each endpoint.
    Delegates business logic to ``ai_suggestions_service``.

For Project Managers:
    Two endpoints power the AI features in the store dashboard:
    POST /stores/{store_id}/products/{product_id}/ai-description
    for product copy generation, and
    POST /stores/{store_id}/products/{product_id}/ai-pricing
    for pricing optimization.

For QA Engineers:
    Test: unauthenticated access (401), store ownership validation (404),
    product existence validation (404), successful description generation,
    successful pricing suggestion, and error handling for malformed AI output.

For End Users:
    Generate AI-powered product descriptions and get pricing suggestions
    for any product in your store. Access these features from the product
    detail page in your dashboard.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.ai_suggestions_service import (
    generate_product_description,
    suggest_pricing,
)
from app.services.store_service import get_store

router = APIRouter(prefix="/stores", tags=["ai-features"])


async def _validate_store_ownership(
    db: AsyncSession, store_id: uuid.UUID, user: User
) -> None:
    """Validate that the store exists and belongs to the current user.

    Uses the existing ``get_store`` service function which checks
    ownership and raises ``ValueError`` if invalid.

    Args:
        db: Async database session.
        store_id: UUID of the store to validate.
        user: The authenticated user.

    Raises:
        HTTPException: 404 if the store does not exist or does not
            belong to the current user.
    """
    try:
        await get_store(db, user.id, store_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )


@router.post("/{store_id}/products/{product_id}/ai-description")
async def ai_description_endpoint(
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate an AI-powered product description.

    Creates compelling, SEO-optimized product copy with title variations,
    descriptions, bullet points, and meta tags.

    Args:
        store_id: UUID of the store (from URL path).
        product_id: UUID of the product (from URL path).
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with description data, product_id, store_id, timestamp,
        provider, and cost.

    Raises:
        HTTPException: 404 if store not found or not owned by user.
    """
    await _validate_store_ownership(db, store_id, current_user)
    return await generate_product_description(
        db, str(store_id), str(product_id)
    )


@router.post("/{store_id}/products/{product_id}/ai-pricing")
async def ai_pricing_endpoint(
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get AI-powered pricing suggestions for a product.

    Analyzes market positioning and provides pricing strategy
    recommendations with competitive analysis.

    Args:
        store_id: UUID of the store (from URL path).
        product_id: UUID of the product (from URL path).
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with pricing recommendations, product_id, store_id,
        timestamp, provider, and cost.

    Raises:
        HTTPException: 404 if store not found or not owned by user.
    """
    await _validate_store_ownership(db, store_id, current_user)
    return await suggest_pricing(db, str(store_id), str(product_id))
