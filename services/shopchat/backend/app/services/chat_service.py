"""
Chat service for handling the core conversation logic.

Receives visitor messages via the widget, searches the knowledge base
for relevant context, generates an AI response (mock implementation),
and returns the response with optional product suggestions.

For Developers:
    The AI response generation is mocked — it builds a context-aware
    reply based on the knowledge base content and message keywords.
    Replace `_generate_ai_response` with actual Claude API calls
    when ready for production.

For QA Engineers:
    Test the full chat flow: send message -> get AI response.
    Verify conversation creation on first message, message counting,
    and product suggestion generation.

For Project Managers:
    This is the core value of ShopChat — the AI-powered chat engine.
    Currently uses mock responses; real AI integration is planned.

For End Users:
    The chat service powers your AI shopping assistant. It uses your
    knowledge base to provide accurate, context-aware responses.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PLAN_LIMITS
from app.models.chatbot import Chatbot
from app.models.conversation import Conversation
from app.models.knowledge_base import KnowledgeBase
from app.models.message import Message
from app.models.user import User


async def count_monthly_conversations(
    db: AsyncSession, user_id: uuid.UUID
) -> int:
    """
    Count conversations this month across all of a user's chatbots.

    Used for plan limit enforcement (max_items = conversations/month).

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Integer count of conversations this billing period.
    """
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count())
        .select_from(Conversation)
        .join(Chatbot, Conversation.chatbot_id == Chatbot.id)
        .where(
            Chatbot.user_id == user_id,
            Conversation.started_at >= month_start,
        )
    )
    return result.scalar() or 0


async def check_conversation_limit(db: AsyncSession, user: User) -> bool:
    """
    Check if the user can start more conversations this month.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        True if within limits, False if at capacity.
    """
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_items == -1:
        return True  # Unlimited

    current_count = await count_monthly_conversations(db, user.id)
    return current_count < plan_limits.max_items


async def get_or_create_conversation(
    db: AsyncSession,
    chatbot: Chatbot,
    visitor_id: str,
    visitor_name: str | None = None,
) -> Conversation:
    """
    Get an existing active conversation or create a new one.

    Looks for an active conversation between this visitor and chatbot.
    If none exists, creates a new one.

    Args:
        db: Async database session.
        chatbot: The chatbot handling the conversation.
        visitor_id: Session-based visitor identifier.
        visitor_name: Optional visitor name.

    Returns:
        The active or newly created Conversation.
    """
    # Look for existing active conversation
    result = await db.execute(
        select(Conversation).where(
            Conversation.chatbot_id == chatbot.id,
            Conversation.visitor_id == visitor_id,
            Conversation.status == "active",
        )
    )
    conversation = result.scalar_one_or_none()

    if conversation:
        if visitor_name and not conversation.visitor_name:
            conversation.visitor_name = visitor_name
        return conversation

    # Create new conversation
    conversation = Conversation(
        chatbot_id=chatbot.id,
        visitor_id=visitor_id,
        visitor_name=visitor_name,
        status="active",
    )
    db.add(conversation)
    await db.flush()
    return conversation


async def add_message(
    db: AsyncSession,
    conversation: Conversation,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> Message:
    """
    Add a message to a conversation and increment the message count.

    Args:
        db: Async database session.
        conversation: The conversation to add the message to.
        role: Message sender role ("user" or "assistant").
        content: Message text content.
        metadata: Optional extra data (product refs, links).

    Returns:
        The newly created Message.
    """
    message = Message(
        conversation_id=conversation.id,
        role=role,
        content=content,
        metadata=metadata,
    )
    db.add(message)
    conversation.message_count += 1
    await db.flush()
    return message


def _search_knowledge_base(
    entries: list[KnowledgeBase], query: str
) -> list[KnowledgeBase]:
    """
    Simple keyword-based search of knowledge base entries.

    Ranks entries by the number of query words found in the title
    and content. Returns the top 3 most relevant entries.

    Args:
        entries: List of active knowledge base entries.
        query: The visitor's message text.

    Returns:
        Top 3 matching KnowledgeBase entries, sorted by relevance.
    """
    query_words = query.lower().split()
    scored = []

    for entry in entries:
        searchable = f"{entry.title} {entry.content}".lower()
        score = sum(1 for word in query_words if word in searchable)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:3]]


def _generate_ai_response(
    chatbot: Chatbot,
    message: str,
    relevant_entries: list[KnowledgeBase],
) -> tuple[str, list[dict]]:
    """
    Generate a mock AI response based on context.

    In production, this would call Claude API with the knowledge base
    context. The mock version builds a contextually aware response
    using the chatbot personality and matched knowledge base entries.

    Args:
        chatbot: The chatbot generating the response.
        message: The visitor's message.
        relevant_entries: Knowledge base entries relevant to the query.

    Returns:
        Tuple of (response text, list of product suggestion dicts).
    """
    # Personality-based greeting adjustments
    personality_prefixes = {
        "friendly": "Great question! ",
        "professional": "Thank you for your inquiry. ",
        "casual": "Hey! ",
        "helpful": "I'd be happy to help! ",
    }
    prefix = personality_prefixes.get(chatbot.personality, "")

    product_suggestions: list[dict] = []

    if relevant_entries:
        # Build response from knowledge base
        top_entry = relevant_entries[0]
        context_snippet = top_entry.content[:300]

        response = (
            f"{prefix}Based on our information about "
            f'"{top_entry.title}": {context_snippet}'
        )

        if len(context_snippet) >= 300:
            response += "..."

        # Generate product suggestions from catalog entries
        for entry in relevant_entries:
            if entry.source_type == "product_catalog":
                product_suggestions.append({
                    "name": entry.title,
                    "price": entry.metadata.get("price", "N/A") if entry.metadata else "N/A",
                    "url": entry.metadata.get("url", "#") if entry.metadata else "#",
                })
    else:
        # No matching knowledge base — generic response
        response = (
            f"{prefix}I don't have specific information about that in my "
            f"knowledge base yet. Could you try rephrasing your question, "
            f"or would you like to know about something else?"
        )

    return response, product_suggestions


async def process_chat_message(
    db: AsyncSession,
    chatbot: Chatbot,
    visitor_id: str,
    message_text: str,
    visitor_name: str | None = None,
) -> tuple[Conversation, Message, str, list[dict]]:
    """
    Process an incoming chat message and generate an AI response.

    This is the main chat flow:
    1. Get or create a conversation for the visitor.
    2. Save the visitor's message.
    3. Search the knowledge base for relevant context.
    4. Generate an AI response (mock).
    5. Save the AI response as a message.

    Args:
        db: Async database session.
        chatbot: The chatbot handling the conversation.
        visitor_id: Session-based visitor identifier.
        message_text: The visitor's message.
        visitor_name: Optional visitor name.

    Returns:
        Tuple of (conversation, ai_message, response_text, product_suggestions).
    """
    # Step 1: Get or create conversation
    conversation = await get_or_create_conversation(
        db, chatbot, visitor_id, visitor_name
    )

    # Step 2: Save user message
    await add_message(db, conversation, "user", message_text)

    # Step 3: Search knowledge base
    from app.services.knowledge_service import get_active_entries_for_chatbot

    entries = await get_active_entries_for_chatbot(db, chatbot.id)
    relevant_entries = _search_knowledge_base(entries, message_text)

    # Step 4: Generate AI response
    response_text, product_suggestions = _generate_ai_response(
        chatbot, message_text, relevant_entries
    )

    # Step 5: Save assistant message
    ai_metadata = None
    if product_suggestions:
        ai_metadata = {"product_suggestions": product_suggestions}

    ai_message = await add_message(
        db, conversation, "assistant", response_text, ai_metadata
    )

    return conversation, ai_message, response_text, product_suggestions


async def end_conversation(
    db: AsyncSession, conversation: Conversation
) -> Conversation:
    """
    Mark a conversation as ended.

    Args:
        db: Async database session.
        conversation: The conversation to end.

    Returns:
        The updated Conversation with ended status.
    """
    conversation.status = "ended"
    conversation.ended_at = datetime.now(UTC)
    await db.flush()
    return conversation


async def rate_conversation(
    db: AsyncSession, conversation: Conversation, score: float
) -> Conversation:
    """
    Set a satisfaction score on a conversation.

    Args:
        db: Async database session.
        conversation: The conversation to rate.
        score: Satisfaction rating from 1.0 to 5.0.

    Returns:
        The updated Conversation with satisfaction score.
    """
    conversation.satisfaction_score = score
    await db.flush()
    return conversation
