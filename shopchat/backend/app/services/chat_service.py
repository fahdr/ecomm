"""
Chat service for handling the core conversation logic.

Receives visitor messages via the widget, searches the knowledge base
for relevant context, generates an AI response using the LLM Gateway
(with mock fallback), and returns the response with optional product
suggestions and tool call results.

For Developers:
    The ``generate_response()`` function is the enhanced entry point for
    LLM-powered chat. It builds conversation context from session history,
    includes relevant knowledge base entries in the system prompt, and
    calls the LLM Gateway with tool-calling capabilities. If the gateway
    is unavailable, it falls back to the mock response generator.

    Available tools for the LLM:
    - ``search_products(query)`` -- search product catalog
    - ``get_order_status(order_id)`` -- lookup order
    - ``get_faq_answer(question)`` -- match FAQ entries

For QA Engineers:
    Test the full chat flow: send message -> get AI response.
    Verify conversation creation on first message, message counting,
    product suggestion generation, and tool call execution.
    Mock the LLM client in tests.

For Project Managers:
    This is the core value of ShopChat — the AI-powered chat engine.
    Now uses the LLM Gateway for real AI responses with mock fallback.

For End Users:
    The chat service powers your AI shopping assistant. It uses your
    knowledge base to provide accurate, context-aware responses.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PLAN_LIMITS
from app.models.chatbot import Chatbot
from app.models.conversation import Conversation
from app.models.knowledge_base import KnowledgeBase
from app.models.message import Message
from app.models.user import User

logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """
    Structured response from the chat AI engine.

    Attributes:
        message_text: The AI assistant's response text.
        suggested_actions: List of suggested follow-up actions for the visitor.
        tool_calls_made: List of tool calls that were executed during response generation.
        confidence_score: Confidence level of the response (0.0-1.0).
    """

    message_text: str
    suggested_actions: list[str] = field(default_factory=list)
    tool_calls_made: list[dict] = field(default_factory=list)
    confidence_score: float = 0.8


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
        extra_metadata=metadata,
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
                    "price": entry.extra_metadata.get("price", "N/A") if entry.extra_metadata else "N/A",
                    "url": entry.extra_metadata.get("url", "#") if entry.extra_metadata else "#",
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
    db: AsyncSession,
    conversation: Conversation,
    score: float,
    feedback: str | None = None,
) -> Conversation:
    """
    Set a satisfaction score and optional feedback on a conversation.

    Args:
        db: Async database session.
        conversation: The conversation to rate.
        score: Satisfaction rating from 1.0 to 5.0.
        feedback: Optional text feedback from the visitor.

    Returns:
        The updated Conversation with satisfaction score.
    """
    conversation.satisfaction_score = score
    await db.flush()
    return conversation


# ── Tool Execution Helpers ──────────────────────────────────────────


async def _tool_search_products(
    db: AsyncSession, chatbot_id: uuid.UUID, query: str
) -> list[dict]:
    """
    Search the product catalog knowledge base entries.

    Used as a tool call during LLM response generation. Searches
    product_catalog entries matching the query keywords.

    Args:
        db: Async database session.
        chatbot_id: The chatbot's UUID to scope the search.
        query: Product search query text.

    Returns:
        List of matching product dicts with name, price, and URL.
    """
    from app.services.knowledge_service import get_active_entries_for_chatbot

    entries = await get_active_entries_for_chatbot(db, chatbot_id)
    catalog_entries = [e for e in entries if e.source_type == "product_catalog"]

    query_words = query.lower().split()
    results = []

    for entry in catalog_entries:
        searchable = f"{entry.title} {entry.content}".lower()
        score = sum(1 for w in query_words if w in searchable)
        if score > 0:
            results.append({
                "name": entry.title,
                "description": entry.content[:200],
                "price": entry.extra_metadata.get("price", "N/A") if entry.extra_metadata else "N/A",
                "url": entry.extra_metadata.get("url", "#") if entry.extra_metadata else "#",
                "score": score,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]


async def _tool_get_faq_answer(
    db: AsyncSession, chatbot_id: uuid.UUID, question: str
) -> str | None:
    """
    Match a visitor question against FAQ knowledge base entries.

    Used as a tool call during LLM response generation. Searches
    FAQ and policy page entries for relevant answers.

    Args:
        db: Async database session.
        chatbot_id: The chatbot's UUID.
        question: The visitor's question text.

    Returns:
        The best matching FAQ answer text, or None if no match found.
    """
    from app.services.knowledge_service import get_active_entries_for_chatbot

    entries = await get_active_entries_for_chatbot(db, chatbot_id)
    faq_entries = [
        e for e in entries if e.source_type in ("faq", "policy_page", "custom_text")
    ]

    query_words = question.lower().split()
    best_match = None
    best_score = 0

    for entry in faq_entries:
        searchable = f"{entry.title} {entry.content}".lower()
        score = sum(1 for w in query_words if w in searchable)
        if score > best_score:
            best_score = score
            best_match = entry

    if best_match and best_score > 0:
        return f"[{best_match.title}]: {best_match.content}"
    return None


def _tool_get_order_status(order_id: str) -> dict:
    """
    Look up order status by order ID.

    Currently returns mock data. In production, this would query
    the platform's order API.

    Args:
        order_id: The order identifier to look up.

    Returns:
        Dict with order status information.
    """
    # Mock implementation -- in production, call the platform API
    return {
        "order_id": order_id,
        "status": "processing",
        "estimated_delivery": "3-5 business days",
        "tracking_number": None,
        "message": f"Order {order_id} is currently being processed.",
    }


async def _execute_tool_calls(
    db: AsyncSession,
    chatbot_id: uuid.UUID,
    tool_calls: list[dict],
) -> list[dict]:
    """
    Execute a list of tool calls and return their results.

    Dispatches each tool call to the appropriate handler function
    based on the tool name.

    Args:
        db: Async database session.
        chatbot_id: The chatbot's UUID for scoping tool queries.
        tool_calls: List of tool call dicts with 'name' and 'arguments'.

    Returns:
        List of tool result dicts with 'tool', 'result' keys.
    """
    results = []
    for call in tool_calls:
        tool_name = call.get("name", "")
        args = call.get("arguments", {})

        if tool_name == "search_products":
            result = await _tool_search_products(
                db, chatbot_id, args.get("query", "")
            )
        elif tool_name == "get_order_status":
            result = _tool_get_order_status(args.get("order_id", ""))
        elif tool_name == "get_faq_answer":
            result = await _tool_get_faq_answer(
                db, chatbot_id, args.get("question", "")
            )
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        results.append({"tool": tool_name, "result": result})

    return results


# ── Enhanced Chat AI ────────────────────────────────────────────────


async def generate_response(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    user_message: str,
    context: dict | None = None,
) -> ChatResponse:
    """
    Generate an LLM-powered AI response for a chat message.

    This is the enhanced chat flow that:
    1. Builds conversation context from session history.
    2. Includes relevant knowledge base entries in system prompt.
    3. Calls the LLM Gateway with tool-calling capabilities.
    4. Parses LLM response for tool calls and executes them.
    5. Falls back to mock response if the gateway is unavailable.

    Args:
        db: Async database session.
        user_id: The chatbot owner's UUID.
        session_id: The conversation/session UUID.
        user_message: The visitor's message text.
        context: Optional additional context dict with:
            - chatbot_id: UUID of the chatbot.
            - chatbot_personality: Personality style string.

    Returns:
        ChatResponse with message_text, suggested_actions,
        tool_calls_made, and confidence_score.
    """
    from app.services.llm_client import call_llm
    from app.services.personality_service import get_system_prompt

    context = context or {}
    chatbot_id = context.get("chatbot_id")

    # Build system prompt from personality config
    system_prompt = await get_system_prompt(
        db, user_id, chatbot_id=chatbot_id
    )

    # Append tool definitions to the system prompt
    tool_instructions = """

You have access to the following tools. To use a tool, include a JSON block in your response like:
```tool_call
{"name": "tool_name", "arguments": {"arg": "value"}}
```

Available tools:
- search_products(query: str) - Search the product catalog for matching products
- get_order_status(order_id: str) - Look up order status by order ID
- get_faq_answer(question: str) - Find FAQ answers matching a question

Only use tools when the visitor's question requires it. Otherwise, respond directly.
"""
    full_system_prompt = system_prompt + tool_instructions

    # Build conversation history for context
    conversation_history = ""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    recent_messages = list(reversed(list(result.scalars().all())))

    for msg in recent_messages:
        role_label = "Customer" if msg.role == "user" else "Assistant"
        conversation_history += f"{role_label}: {msg.content}\n"

    conversation_history += f"Customer: {user_message}\nAssistant:"

    # Try calling the LLM Gateway
    llm_result = await call_llm(
        prompt=conversation_history,
        system=full_system_prompt,
        user_id=str(user_id),
        task_type="chat",
        max_tokens=1000,
        temperature=0.7,
    )

    tool_calls_made = []
    suggested_actions = []

    if llm_result and llm_result.get("content"):
        response_text = llm_result["content"]

        # Parse for tool calls in the response
        if "```tool_call" in response_text:
            import re

            tool_pattern = r"```tool_call\s*\n?(.*?)\n?```"
            matches = re.findall(tool_pattern, response_text, re.DOTALL)

            parsed_calls = []
            for match in matches:
                try:
                    call_data = json.loads(match.strip())
                    parsed_calls.append(call_data)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse tool call: %s", match)

            if parsed_calls and chatbot_id:
                # Execute tool calls
                tool_results = await _execute_tool_calls(db, chatbot_id, parsed_calls)
                tool_calls_made = tool_results

                # Remove tool call blocks from response and append results
                clean_text = re.sub(tool_pattern, "", response_text, flags=re.DOTALL).strip()
                if tool_results:
                    for tr in tool_results:
                        if tr["tool"] == "search_products" and isinstance(tr["result"], list):
                            for product in tr["result"][:3]:
                                clean_text += f"\n- {product['name']}: {product.get('price', 'N/A')}"
                        elif tr["tool"] == "get_faq_answer" and tr["result"]:
                            clean_text += f"\n{tr['result']}"
                        elif tr["tool"] == "get_order_status" and isinstance(tr["result"], dict):
                            clean_text += f"\n{tr['result'].get('message', '')}"

                response_text = clean_text

        return ChatResponse(
            message_text=response_text,
            suggested_actions=suggested_actions,
            tool_calls_made=tool_calls_made,
            confidence_score=0.9,
        )

    # Fallback to mock response if LLM is unavailable
    logger.info("LLM Gateway unavailable, using mock response")

    # Use the existing mock logic
    from app.services.knowledge_service import get_active_entries_for_chatbot

    entries = []
    if chatbot_id:
        entries = await get_active_entries_for_chatbot(db, chatbot_id)
    relevant = _search_knowledge_base(entries, user_message)

    personality = context.get("chatbot_personality", "friendly")

    # Build mock response
    personality_prefixes = {
        "friendly": "Great question! ",
        "professional": "Thank you for your inquiry. ",
        "casual": "Hey! ",
        "helpful": "I'd be happy to help! ",
    }
    prefix = personality_prefixes.get(personality, "")

    if relevant:
        top_entry = relevant[0]
        content_snippet = top_entry.content[:300]
        response_text = (
            f"{prefix}Based on our information about "
            f'"{top_entry.title}": {content_snippet}'
        )
        if len(content_snippet) >= 300:
            response_text += "..."

        for entry in relevant:
            if entry.source_type == "product_catalog":
                suggested_actions.append(f"View {entry.title}")
    else:
        response_text = (
            f"{prefix}I don't have specific information about that in my "
            f"knowledge base yet. Could you try rephrasing your question, "
            f"or would you like to know about something else?"
        )

    return ChatResponse(
        message_text=response_text,
        suggested_actions=suggested_actions,
        tool_calls_made=[],
        confidence_score=0.6,
    )
