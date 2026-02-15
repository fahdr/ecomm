"""
AI suggestions API router for FlowSend.

Exposes endpoints for AI-driven campaign copy generation, customer
segmentation, and marketing improvement suggestions.
All endpoints require JWT authentication.

For Developers:
    Mount this router in ``main.py`` with prefix ``/api/v1``.
    Uses ``get_current_user`` from ``app.main`` for authentication.
    Delegates business logic to ``ai_suggestions_service``.

For Project Managers:
    Three endpoints power the AI features in the FlowSend dashboard:
    GET /ai/suggestions for general advice, POST /ai/generate-copy
    for campaign copywriting, POST /ai/segment-contacts for segmentation.

For QA Engineers:
    Test: unauthenticated access (401), campaign copy generation with
    various inputs, segmentation retrieval, and error handling.

For End Users:
    Generate AI-powered campaign copy, segment your contacts
    intelligently, and get marketing improvement suggestions from
    your FlowSend dashboard.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_current_user
from app.models.user import User
from app.services.ai_suggestions_service import (
    ai_segment_contacts,
    generate_campaign_copy,
    get_ai_suggestions,
)

router = APIRouter(prefix="/ai", tags=["ai"])


class GenerateCopyRequest(BaseModel):
    """Request body for campaign copy generation.

    Attributes:
        campaign_name: Name/theme of the campaign.
        audience: Target audience description.
    """

    campaign_name: str
    audience: str


@router.get("/suggestions")
async def ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get AI-powered campaign improvement suggestions.

    Returns actionable recommendations for email and SMS marketing
    strategy, send timing, and personalization.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with suggestions list, generation timestamp, provider, and cost.
    """
    return await get_ai_suggestions(db, str(current_user.id))


@router.post("/generate-copy")
async def generate_copy_endpoint(
    request: GenerateCopyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate AI-powered campaign copy variants.

    Creates email subject lines, body content, and SMS versions
    tailored to the specified campaign and audience.

    Args:
        request: Contains campaign_name and audience description.
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with copy_variants list, campaign_name, timestamp, provider, cost.
    """
    return await generate_campaign_copy(
        db, str(current_user.id), request.campaign_name, request.audience
    )


@router.post("/segment-contacts")
async def segment_contacts_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate AI-driven customer segmentation recommendations.

    Suggests intelligent contact segments based on behavioral
    patterns and engagement data.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with segments list, timestamp, provider, and cost.
    """
    return await ai_segment_contacts(db, str(current_user.id))
