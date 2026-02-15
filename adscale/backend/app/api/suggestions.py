"""
AI suggestions API router for AdScale.

Exposes endpoints for AI-driven ad copy optimization and campaign
improvement suggestions. All endpoints require JWT authentication.

For Developers:
    Mount this router in ``main.py`` with prefix ``/api/v1``.
    Uses ``get_current_user`` from ``app.main`` for authentication.
    Delegates business logic to ``ai_suggestions_service``.

For Project Managers:
    Two endpoints power the AI features in the AdScale dashboard:
    GET /ai/suggestions for general ad advice,
    POST /ai/optimize-ad for targeted ad optimization.

For QA Engineers:
    Test: unauthenticated access (401), successful suggestion retrieval,
    ad optimization with valid/invalid ad_id, and error handling.

For End Users:
    Optimize your ad campaigns with AI-powered copy improvements
    and targeting suggestions from your AdScale dashboard.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_current_user
from app.models.user import User
from app.services.ai_suggestions_service import get_ai_suggestions, optimize_ad

router = APIRouter(prefix="/ai", tags=["ai"])


class OptimizeAdRequest(BaseModel):
    """Request body for ad optimization.

    Attributes:
        ad_id: UUID string of the ad to optimize.
    """

    ad_id: str


@router.get("/suggestions")
async def ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get AI-powered ad campaign improvement suggestions.

    Returns actionable recommendations for budget optimization,
    targeting, creative strategy, and retargeting.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with suggestions list, generation timestamp, provider, and cost.
    """
    return await get_ai_suggestions(db, str(current_user.id))


@router.post("/optimize-ad")
async def optimize_ad_endpoint(
    request: OptimizeAdRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Optimize a specific ad with AI analysis.

    Provides improvements for headlines, body copy, CTA text,
    and audience targeting with expected performance lifts.

    Args:
        request: Contains the ad_id to optimize.
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with optimizations list, ad_id, timestamp, provider, and cost.
    """
    return await optimize_ad(db, str(current_user.id), request.ad_id)
