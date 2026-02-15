"""
Public widget API routes (NO authentication required).

These endpoints are used by the embeddable chat widget on external
websites. They use the widget_key to identify the chatbot instead
of JWT authentication. Also serves the embeddable JavaScript widget
script.

For Developers:
    IMPORTANT: These endpoints are PUBLIC -- no JWT or API key required.
    They authenticate via the widget_key parameter, which maps to a
    specific chatbot. Rate limiting should be applied in production.
    The script.js endpoint serves the full widget JavaScript.

For QA Engineers:
    Test these endpoints WITHOUT auth headers. Verify they work with
    only the widget_key. Test with invalid widget_keys (should 404).
    Test with inactive chatbots (should 404). Test the script.js
    endpoint returns valid JavaScript with correct Content-Type.

For Project Managers:
    These are the endpoints that external websites call when visitors
    interact with the embedded chat widget. They must be fast and
    reliable -- any downtime means lost customer interactions.

For End Users:
    These endpoints power the chat widget on your website. They do
    not require login -- visitors can chat immediately.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ProductSuggestion, WidgetConfig
from app.services.chat_service import check_conversation_limit, process_chat_message
from app.services.chatbot_service import get_chatbot_by_widget_key
from app.services.widget_service import generate_widget_script, generate_widget_snippet

router = APIRouter(prefix="/widget", tags=["widget"])


@router.get("/config/{widget_key}", response_model=WidgetConfig)
async def get_widget_config(
    widget_key: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get widget configuration for rendering the chat widget.

    PUBLIC endpoint — no authentication required. Uses the widget_key
    to identify the chatbot and returns its display configuration.

    Args:
        widget_key: The chatbot's unique widget key.
        db: Database session.

    Returns:
        WidgetConfig with chatbot name, personality, theme, etc.

    Raises:
        HTTPException: 404 if widget_key is invalid or chatbot is inactive.
    """
    chatbot = await get_chatbot_by_widget_key(db, widget_key)
    if not chatbot or not chatbot.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found or inactive",
        )

    return WidgetConfig(
        chatbot_name=chatbot.name,
        personality=chatbot.personality,
        welcome_message=chatbot.welcome_message,
        theme_config=chatbot.theme_config,
        is_active=chatbot.is_active,
    )


@router.post("/chat", response_model=ChatResponse)
async def widget_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a chat message via the widget and receive an AI response.

    PUBLIC endpoint — no authentication required. Uses the widget_key
    to identify the chatbot. Creates or continues a conversation for
    the visitor, generates an AI response, and returns it with optional
    product suggestions.

    Args:
        body: Chat request with widget_key, visitor_id, and message.
        db: Database session.

    Returns:
        ChatResponse with the AI message and product suggestions.

    Raises:
        HTTPException: 404 if chatbot not found, 429 if conversation limit reached.
    """
    # Find chatbot by widget key
    chatbot = await get_chatbot_by_widget_key(db, body.widget_key)
    if not chatbot or not chatbot.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found or inactive",
        )

    # Check conversation limits for the chatbot owner
    from sqlalchemy import select
    from app.models.user import User as UserModel

    result = await db.execute(
        select(UserModel).where(UserModel.id == chatbot.user_id)
    )
    owner = result.scalar_one_or_none()
    if owner:
        within_limit = await check_conversation_limit(db, owner)
        if not within_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Conversation limit reached for this chatbot's plan.",
            )

    # Process the message
    conversation, ai_message, response_text, product_suggestions = (
        await process_chat_message(
            db=db,
            chatbot=chatbot,
            visitor_id=body.visitor_id,
            message_text=body.message,
            visitor_name=body.visitor_name,
        )
    )

    return ChatResponse(
        conversation_id=conversation.id,
        message=response_text,
        product_suggestions=[
            ProductSuggestion(**ps) for ps in product_suggestions
        ],
    )


@router.get("/{widget_id}/script.js")
async def get_widget_script(
    widget_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Serve the embeddable JavaScript widget for a chatbot.

    PUBLIC endpoint -- no authentication required. Returns a JavaScript
    file that creates the chat widget UI when loaded in a browser.

    Args:
        widget_id: The chatbot's unique widget key.
        db: Database session.

    Returns:
        JavaScript file content with application/javascript Content-Type.

    Raises:
        HTTPException: 404 if widget_id is invalid or chatbot is inactive.
    """
    chatbot = await get_chatbot_by_widget_key(db, widget_id)
    if not chatbot or not chatbot.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found or inactive",
        )

    config = {
        "position": chatbot.theme_config.get("position", "bottom-right"),
        "theme": "light",
        "greeting": chatbot.welcome_message,
        "primary_color": chatbot.theme_config.get("primary_color", "#6366f1"),
        "text_color": chatbot.theme_config.get("text_color", "#ffffff"),
        "chatbot_name": chatbot.name,
    }

    script_content = generate_widget_script(widget_id, config)
    return Response(
        content=script_content,
        media_type="application/javascript",
    )


@router.get("/{widget_id}/snippet")
async def get_widget_snippet(
    widget_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the embeddable HTML snippet for a chatbot widget.

    PUBLIC endpoint -- returns the HTML script tag that users can
    copy-paste into their website to embed the chat widget.

    Args:
        widget_id: The chatbot's unique widget key.
        db: Database session.

    Returns:
        Dict with 'snippet' containing the HTML script tag.

    Raises:
        HTTPException: 404 if widget_id is invalid or chatbot is inactive.
    """
    chatbot = await get_chatbot_by_widget_key(db, widget_id)
    if not chatbot or not chatbot.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found or inactive",
        )

    config = {
        "position": chatbot.theme_config.get("position", "bottom-right"),
        "theme": "light",
        "greeting": chatbot.welcome_message,
        "primary_color": chatbot.theme_config.get("primary_color", "#6366f1"),
        "text_color": chatbot.theme_config.get("text_color", "#ffffff"),
    }

    snippet = generate_widget_snippet(widget_id, config)
    return {"snippet": snippet, "widget_id": widget_id}
