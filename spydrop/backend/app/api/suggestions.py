"""
AI suggestions API router for SpyDrop.

Exposes endpoints for AI-driven competitor analysis and competitive
intelligence suggestions. All endpoints require JWT authentication.

For Developers:
    Mount this router in ``main.py`` with prefix ``/api/v1``.
    Uses ``get_current_user`` from ``app.main`` for authentication.
    Delegates business logic to ``ai_suggestions_service``.

For Project Managers:
    Two endpoints power the AI features in the SpyDrop dashboard:
    GET /ai/suggestions for general competitive advice,
    POST /ai/competitor-analysis for detailed competitor insights.

For QA Engineers:
    Test: unauthenticated access (401), successful suggestion retrieval,
    competitor analysis with valid/invalid competitor_id, and error handling.

For End Users:
    Access AI-powered competitor analysis and competitive intelligence
    from your SpyDrop dashboard. Analyze specific competitors or get
    general strategic advice.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_current_user
from app.models.user import User
from app.services.ai_suggestions_service import analyze_competitor, get_ai_suggestions

router = APIRouter(prefix="/ai", tags=["ai"])


class CompetitorAnalysisRequest(BaseModel):
    """Request body for competitor analysis.

    Attributes:
        competitor_id: UUID string of the competitor to analyze.
    """

    competitor_id: str


@router.get("/suggestions")
async def ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get AI-powered competitive intelligence suggestions.

    Returns strategic recommendations for competitive positioning,
    market differentiation, and opportunity identification.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with suggestions list, generation timestamp, provider, and cost.
    """
    return await get_ai_suggestions(db, str(current_user.id))


@router.post("/competitor-analysis")
async def competitor_analysis_endpoint(
    request: CompetitorAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate detailed AI competitor analysis.

    Analyzes a specific competitor's pricing, products, marketing,
    and positioning to provide actionable counter-strategies.

    Args:
        request: Contains the competitor_id to analyze.
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with analysis list, competitor_id, timestamp, provider, and cost.
    """
    return await analyze_competitor(
        db, str(current_user.id), request.competitor_id
    )
