"""
AI suggestions API router for SourcePilot.

Exposes endpoints for AI-driven supplier scoring and sourcing
improvement suggestions. All endpoints require JWT authentication.

For Developers:
    Mount this router in ``main.py`` with prefix ``/api/v1``.
    Uses ``get_current_user`` from ``app.api.deps`` for authentication.
    Delegates business logic to ``ai_suggestions_service``.

For Project Managers:
    Two endpoints power the AI features in the SourcePilot dashboard:
    GET /ai/suggestions for general sourcing advice,
    POST /ai/score-supplier for AI supplier reliability scoring.

For QA Engineers:
    Test: unauthenticated access (401), successful suggestion retrieval,
    supplier scoring with various URLs, and error handling.

For End Users:
    Score suppliers with AI-powered reliability analysis and get
    sourcing strategy suggestions from your SourcePilot dashboard.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.ai_suggestions_service import get_ai_suggestions, score_supplier

router = APIRouter(prefix="/ai", tags=["ai"])


class ScoreSupplierRequest(BaseModel):
    """Request body for supplier scoring.

    Attributes:
        supplier_url: URL of the supplier to evaluate.
    """

    supplier_url: str


@router.get("/suggestions")
async def ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get AI-powered supplier sourcing suggestions.

    Returns actionable recommendations for supplier diversification,
    quality control, and cost optimization.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with suggestions list, generation timestamp, provider, and cost.
    """
    return await get_ai_suggestions(db, str(current_user.id))


@router.post("/score-supplier")
async def score_supplier_endpoint(
    request: ScoreSupplierRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Score a supplier with AI reliability analysis.

    Evaluates a supplier across multiple dimensions including
    product quality, shipping, communication, and pricing.

    Args:
        request: Contains the supplier_url to evaluate.
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with scoring breakdown, overall_score, supplier_url,
        timestamp, provider, and cost.
    """
    return await score_supplier(db, str(current_user.id), request.supplier_url)
