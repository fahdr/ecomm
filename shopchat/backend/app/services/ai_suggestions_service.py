"""
AI-driven suggestions service for ShopChat.

Provides intelligent chatbot knowledge enhancement and improvement
suggestions through the centralized LLM Gateway.

For Developers:
    Uses ``call_llm()`` from ``ecomm_core.llm_client`` to route requests
    through the LLM Gateway. Two functions: ``train_assistant`` for
    enhancing chatbot knowledge, and ``get_ai_suggestions`` for general
    chatbot improvement advice.

For Project Managers:
    AI knowledge enhancement helps merchants build smarter chatbots
    that better serve their customers. Each call consumes LLM tokens
    billed through the gateway.

For QA Engineers:
    Mock ``call_llm`` in tests using ``call_llm_mock`` from ecomm_core.
    Test knowledge enhancement with various knowledge base inputs.
    Verify JSON parsing fallback when LLM returns malformed output.

For End Users:
    Enhance your chatbot's knowledge and get improvement suggestions
    from the ShopChat dashboard. The AI helps your chatbot provide
    better customer support and product recommendations.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.llm_client import call_llm

from app.config import settings


async def train_assistant(
    db: AsyncSession, user_id: str, knowledge_base: str
) -> dict:
    """Enhance chatbot knowledge with AI-processed training data.

    Takes raw knowledge base text and generates structured FAQ entries,
    response templates, and conversation flows.

    Args:
        db: Async database session.
        user_id: The authenticated user's UUID string.
        knowledge_base: Raw text containing product info, policies, etc.

    Returns:
        Dict containing:
            - training_data: Structured knowledge entries for the chatbot.
            - generated_at: ISO timestamp of when training was generated.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            f"Process the following knowledge base text and generate "
            f"structured training data for a customer support chatbot:\n\n"
            f"{knowledge_base[:3000]}\n\n"
            "Generate: FAQ pairs (question + answer), response templates "
            "for common scenarios (shipping, returns, sizing), product "
            "recommendation logic, and escalation triggers. Return JSON "
            "with a 'training_data' object containing 'faqs' array, "
            "'templates' array, 'recommendations' array, and "
            "'escalation_rules' array."
        ),
        system=(
            "You are an expert conversational AI designer specializing "
            "in e-commerce chatbots. You create helpful, accurate, and "
            "brand-appropriate chatbot responses. Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="chatbot_training",
        max_tokens=2000,
        temperature=0.5,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"training_data": {"raw": result.get("content", "No training data generated.")}}

    return {
        "training_data": parsed.get("training_data", parsed),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }


async def get_ai_suggestions(db: AsyncSession, user_id: str) -> dict:
    """Suggest chatbot improvements and optimization strategies.

    Provides actionable recommendations for improving chatbot
    performance, customer satisfaction, and conversion rates.

    Args:
        db: Async database session for querying user data.
        user_id: The authenticated user's UUID string.

    Returns:
        Dict containing:
            - suggestions: List of chatbot improvement suggestions.
            - generated_at: ISO timestamp of generation.
            - provider: The LLM provider used.
            - cost_usd: Cost of the LLM call in USD.
    """
    result = await call_llm(
        prompt=(
            "Provide 3-5 actionable suggestions to improve an e-commerce "
            "chatbot. Cover: conversation flow optimization, knowledge "
            "base expansion, tone and personality refinement, proactive "
            "engagement triggers, and escalation handling. Return JSON "
            "with a 'suggestions' array of objects, each with 'title', "
            "'description', and 'priority' (high/medium/low)."
        ),
        system=(
            "You are an expert in conversational AI and customer "
            "experience for e-commerce. You help merchants build "
            "chatbots that delight customers and drive sales. "
            "Always return valid JSON."
        ),
        user_id=user_id,
        service_name=settings.service_name,
        task_type="chatbot_suggestions",
        max_tokens=1000,
        temperature=0.7,
        json_mode=True,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
    )

    try:
        parsed = json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        parsed = {"suggestions": [result.get("content", "No suggestions available.")]}

    return {
        "suggestions": parsed.get("suggestions", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": result.get("provider", "unknown"),
        "cost_usd": result.get("cost_usd", 0),
    }
