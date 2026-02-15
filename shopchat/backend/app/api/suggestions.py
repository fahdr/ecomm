"""
AI suggestions API router for ShopChat.

Exposes endpoints for AI-driven chatbot knowledge enhancement and
improvement suggestions. All endpoints require JWT authentication.

For Developers:
    Mount this router in ``main.py`` with prefix ``/api/v1``.
    Uses ``get_current_user`` from ``app.main`` for authentication.
    Delegates business logic to ``ai_suggestions_service``.

For Project Managers:
    Two endpoints power the AI features in the ShopChat dashboard:
    GET /ai/suggestions for general chatbot advice,
    POST /ai/train-assistant for knowledge base enhancement.

For QA Engineers:
    Test: unauthenticated access (401), successful suggestion retrieval,
    assistant training with various knowledge base inputs, and error handling.

For End Users:
    Enhance your chatbot's knowledge and get improvement suggestions
    from your ShopChat dashboard.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_current_user
from app.models.user import User
from app.services.ai_suggestions_service import get_ai_suggestions, train_assistant

router = APIRouter(prefix="/ai", tags=["ai"])


class TrainAssistantRequest(BaseModel):
    """Request body for chatbot training.

    Attributes:
        knowledge_base: Raw text containing product info, policies, FAQs.
    """

    knowledge_base: str


@router.get("/suggestions")
async def ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get AI-powered chatbot improvement suggestions.

    Returns actionable recommendations for conversation flow,
    knowledge base, tone, and engagement optimization.

    Args:
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with suggestions list, generation timestamp, provider, and cost.
    """
    return await get_ai_suggestions(db, str(current_user.id))


@router.post("/train-assistant")
async def train_assistant_endpoint(
    request: TrainAssistantRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Enhance chatbot knowledge with AI-processed training data.

    Processes raw knowledge base text and generates structured
    FAQ entries, response templates, and conversation flows.

    Args:
        request: Contains knowledge_base text to process.
        db: Async database session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        Dict with training_data, timestamp, provider, and cost.
    """
    return await train_assistant(
        db, str(current_user.id), request.knowledge_base
    )
