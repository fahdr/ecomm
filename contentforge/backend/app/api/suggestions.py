"""
AI suggestions API router for ContentForge.

Exposes endpoints for AI-driven content enhancement and improvement
suggestions. All endpoints require JWT authentication.

For Developers:
    Mount this router in ``main.py`` with prefix ``/api/v1``.
    Uses ``get_current_user`` from ``app.main`` for authentication.
    Delegates business logic to ``ai_suggestions_service``.

For Project Managers:
    Two endpoints power the AI features in the ContentForge dashboard:
    GET /ai/suggestions for general content advice,
    POST /ai/enhance-content for targeted content improvement.

For QA Engineers:
    Test: unauthenticated access (401), successful suggestion retrieval,
    content enhancement with valid/invalid content_id, and error handling.

For End Users:
    Access AI-powered content improvement suggestions from your
    ContentForge dashboard. Enhance specific content pieces or get
    general content strategy advice.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_current_user
from app.models.user import User
from app.services.ai_suggestions_service import enhance_content, get_ai_suggestions

router = APIRouter(prefix="/ai", tags=["ai"])


class EnhanceContentRequest(BaseModel):
    """Request body for content enhancement.

    Attributes:
        content_id: UUID string of the content piece to enhance.
    """

    content_id: str


@router.get("/suggestions")
async def ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get AI-powered content improvement suggestions.

    Returns actionable recommendations for content strategy,
    SEO optimization, and engagement improvements.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with suggestions list, generation timestamp, provider, and cost.
    """
    return await get_ai_suggestions(db, str(current_user.id))


@router.post("/enhance-content")
async def enhance_content_endpoint(
    request: EnhanceContentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Enhance a specific content piece with AI analysis.

    Analyzes the content for SEO, readability, and engagement,
    then provides specific improvement suggestions.

    Args:
        request: Contains the content_id to enhance.
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with enhancements list, content_id, timestamp, provider, and cost.
    """
    return await enhance_content(db, str(current_user.id), request.content_id)
