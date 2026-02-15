"""
AI suggestions API router for TrendScout.

Exposes endpoints for AI-driven trend predictions and product research
suggestions. All endpoints require JWT authentication.

For Developers:
    Mount this router in ``main.py`` with prefix ``/api/v1``.
    Uses ``get_current_user`` from ``app.main`` for authentication.
    Delegates business logic to ``ai_suggestions_service``.

For Project Managers:
    Two endpoints power the AI features in the TrendScout dashboard:
    GET /ai/suggestions for general advice, POST /ai/predict-trends
    for detailed trend forecasting.

For QA Engineers:
    Test: unauthenticated access (401), successful suggestion retrieval,
    successful trend prediction, and error handling for malformed AI responses.

For End Users:
    Access AI-powered product research suggestions and trend predictions
    from your TrendScout dashboard. The AI analyzes market data to help
    you find winning products.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_current_user
from app.models.user import User
from app.services.ai_suggestions_service import get_ai_suggestions, predict_trends

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/suggestions")
async def ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get AI-powered product research suggestions.

    Returns actionable recommendations to improve research strategy,
    identify market gaps, and optimize product selection.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with suggestions list, generation timestamp, provider, and cost.
    """
    return await get_ai_suggestions(db, str(current_user.id))


@router.post("/predict-trends")
async def predict_trends_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Trigger AI trend prediction analysis.

    Analyzes market data and predicts upcoming product trends with
    confidence scores and recommended actions.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with predictions list, generation timestamp, provider, and cost.
    """
    return await predict_trends(db, str(current_user.id))
