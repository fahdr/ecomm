"""
AI suggestions API router for PostPilot.

Exposes endpoints for AI-driven caption generation and social media
strategy suggestions. All endpoints require JWT authentication.

For Developers:
    Mount this router in ``main.py`` with prefix ``/api/v1``.
    Uses ``get_current_user`` from ``app.main`` for authentication.
    Delegates business logic to ``ai_suggestions_service``.

For Project Managers:
    Two endpoints power the AI features in the PostPilot dashboard:
    GET /ai/suggestions for general social media advice,
    POST /ai/generate-caption for platform-specific caption creation.

For QA Engineers:
    Test: unauthenticated access (401), successful suggestion retrieval,
    caption generation with various platform/tone combos, and error handling.

For End Users:
    Generate AI-powered social media captions and get posting strategy
    suggestions from your PostPilot dashboard.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_current_user
from app.models.user import User
from app.services.ai_suggestions_service import generate_caption, get_ai_suggestions

router = APIRouter(prefix="/ai", tags=["ai"])


class GenerateCaptionRequest(BaseModel):
    """Request body for caption generation.

    Attributes:
        topic: The topic or product to write about.
        platform: Target social media platform.
        tone: Desired tone for the caption.
    """

    topic: str
    platform: str
    tone: str


@router.get("/suggestions")
async def ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get AI-powered social media strategy suggestions.

    Returns actionable recommendations for content planning,
    engagement tactics, and platform-specific best practices.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with suggestions list, generation timestamp, provider, and cost.
    """
    return await get_ai_suggestions(db, str(current_user.id))


@router.post("/generate-caption")
async def generate_caption_endpoint(
    request: GenerateCaptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate AI-powered social media captions.

    Creates platform-optimized caption variants with hashtags
    and call-to-action elements.

    Args:
        request: Contains topic, platform, and tone.
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with captions list, platform, tone, timestamp, provider, cost.
    """
    return await generate_caption(
        db, str(current_user.id), request.topic, request.platform, request.tone
    )
