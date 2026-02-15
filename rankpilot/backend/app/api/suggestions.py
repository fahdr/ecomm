"""
AI suggestions API router for RankPilot.

Exposes endpoints for AI-driven SEO recommendations and optimization
suggestions. All endpoints require JWT authentication.

For Developers:
    Mount this router in ``main.py`` with prefix ``/api/v1``.
    Uses ``get_current_user`` from ``app.main`` for authentication.
    Delegates business logic to ``ai_suggestions_service``.

For Project Managers:
    Two endpoints power the AI features in the RankPilot dashboard:
    GET /ai/suggestions for general SEO advice,
    POST /ai/seo-suggest for detailed SEO recommendations.

For QA Engineers:
    Test: unauthenticated access (401), successful suggestion retrieval,
    successful SEO recommendation generation, and error handling.

For End Users:
    Access AI-powered SEO recommendations from your RankPilot dashboard.
    Get both quick-win suggestions and in-depth SEO analysis.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_current_user
from app.models.user import User
from app.services.ai_suggestions_service import get_ai_suggestions, seo_suggest

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/suggestions")
async def ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get AI-powered SEO improvement suggestions.

    Returns strategic SEO advice covering keyword research,
    on-page optimization, and competitive positioning.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with suggestions list, generation timestamp, provider, and cost.
    """
    return await get_ai_suggestions(db, str(current_user.id))


@router.post("/seo-suggest")
async def seo_suggest_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate detailed AI SEO recommendations.

    Analyzes keyword data, technical SEO, content strategy,
    and backlink opportunities to provide prioritized action items.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with recommendations list, timestamp, provider, and cost.
    """
    return await seo_suggest(db, str(current_user.id))
