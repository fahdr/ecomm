"""
Personality configuration service for the ShopChat AI assistant.

Manages CRUD operations for chat personality settings and generates
dynamic system prompts that combine personality configuration with
knowledge base context to produce context-aware, personalized AI
responses.

For Developers:
    ``get_system_prompt()`` is the key function — it builds the complete
    system instruction for the LLM by combining the personality config
    (tone, language, name) with a summary of the knowledge base content.
    If no personality config exists, defaults are used.

For QA Engineers:
    Test system prompt generation with and without personality config.
    Verify that tone, language, and bot_name are reflected in the prompt.
    Test that knowledge base entries are included in the prompt context.

For Project Managers:
    Personality configuration directly affects the quality of AI
    responses. The system prompt is the "instruction manual" that
    tells the AI how to behave for each user's chatbot.

For End Users:
    Customize your AI assistant's personality in Settings to match
    your brand voice. The AI will use your settings when responding
    to customers.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personality import ChatPersonality
from app.services.knowledge_service import get_active_entries_for_chatbot


async def get_personality(
    db: AsyncSession, user_id: uuid.UUID
) -> ChatPersonality | None:
    """
    Get the personality configuration for a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        The ChatPersonality if configured, None otherwise.
    """
    result = await db.execute(
        select(ChatPersonality).where(ChatPersonality.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_or_update_personality(
    db: AsyncSession,
    user_id: uuid.UUID,
    greeting_message: str = "Hi there! How can I help you today?",
    tone: str = "friendly",
    bot_name: str = "ShopChat Assistant",
    escalation_rules: dict | None = None,
    response_language: str = "en",
    custom_instructions: str | None = None,
) -> ChatPersonality:
    """
    Create or update the personality configuration for a user.

    If a personality config already exists, updates it. Otherwise
    creates a new one. Each user can have at most one personality config.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        greeting_message: Custom greeting for visitors.
        tone: Response tone (friendly, professional, casual).
        bot_name: Display name for the AI assistant.
        escalation_rules: JSON rules for human escalation triggers.
        response_language: ISO 639-1 language code.
        custom_instructions: Additional AI instructions.

    Returns:
        The created or updated ChatPersonality record.
    """
    existing = await get_personality(db, user_id)

    if existing:
        existing.greeting_message = greeting_message
        existing.tone = tone
        existing.bot_name = bot_name
        existing.escalation_rules = escalation_rules
        existing.response_language = response_language
        existing.custom_instructions = custom_instructions
        await db.flush()
        return existing

    personality = ChatPersonality(
        user_id=user_id,
        greeting_message=greeting_message,
        tone=tone,
        bot_name=bot_name,
        escalation_rules=escalation_rules,
        response_language=response_language,
        custom_instructions=custom_instructions,
    )
    db.add(personality)
    await db.flush()
    return personality


async def get_system_prompt(
    db: AsyncSession,
    user_id: uuid.UUID,
    chatbot_id: uuid.UUID | None = None,
) -> str:
    """
    Build a dynamic system prompt from personality config and knowledge base.

    Combines the user's personality settings (tone, language, bot name)
    with a summary of active knowledge base entries to produce a
    context-aware system instruction for the LLM.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        chatbot_id: Optional chatbot UUID to include specific knowledge base context.

    Returns:
        Complete system prompt string for the LLM.
    """
    personality = await get_personality(db, user_id)

    # Use defaults if no personality is configured
    bot_name = personality.bot_name if personality else "ShopChat Assistant"
    tone = personality.tone if personality else "friendly"
    language = personality.response_language if personality else "en"
    custom_instructions = personality.custom_instructions if personality else None
    escalation_rules = personality.escalation_rules if personality else None

    # Tone descriptions
    tone_descriptions = {
        "friendly": "warm, approachable, and enthusiastic",
        "professional": "formal, courteous, and precise",
        "casual": "relaxed, conversational, and informal",
    }
    tone_desc = tone_descriptions.get(tone, "helpful and clear")

    # Build system prompt
    prompt_parts = [
        f"You are {bot_name}, an AI shopping assistant.",
        f"Respond in a {tone_desc} tone.",
        f"Respond in the language with ISO code: {language}.",
        "Help customers find products, answer questions about orders, and provide information from the store's knowledge base.",
        "If you cannot answer a question, politely suggest the customer contact support.",
        "Keep responses concise but helpful. Use bullet points for lists.",
    ]

    # Add custom instructions if set
    if custom_instructions:
        prompt_parts.append(f"\nAdditional instructions: {custom_instructions}")

    # Add escalation rules if configured
    if escalation_rules:
        rules_text = []
        keywords = escalation_rules.get("keywords", [])
        if keywords:
            rules_text.append(f"Escalate to human support when the customer mentions: {', '.join(keywords)}")
        threshold = escalation_rules.get("frustration_threshold")
        if threshold:
            rules_text.append(f"Escalate if the customer seems frustrated after {threshold} messages.")
        if rules_text:
            prompt_parts.append("\nEscalation rules:\n" + "\n".join(f"- {r}" for r in rules_text))

    # Add knowledge base context if chatbot_id is provided
    if chatbot_id:
        entries = await get_active_entries_for_chatbot(db, chatbot_id)
        if entries:
            kb_summary_parts = ["\n--- Knowledge Base ---"]
            for entry in entries[:20]:  # Limit to 20 entries to stay within token limits
                content_preview = entry.content[:200]
                if len(entry.content) > 200:
                    content_preview += "..."
                kb_summary_parts.append(f"[{entry.source_type}] {entry.title}: {content_preview}")
            prompt_parts.append("\n".join(kb_summary_parts))
            prompt_parts.append("\nUse the above knowledge base entries to answer questions accurately.")

    return "\n".join(prompt_parts)
