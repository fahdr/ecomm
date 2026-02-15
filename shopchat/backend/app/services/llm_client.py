"""
LLM Gateway client for ShopChat AI responses.

Provides a simple async HTTP client that communicates with the centralized
LLM Gateway service for generating AI completions. All AI requests flow
through the gateway for cost tracking, caching, and rate limiting.

For Developers:
    Use ``call_llm()`` to generate AI responses. The function handles
    authentication via the ``X-Service-Key`` header and returns the
    parsed response dict. On failure (network error, gateway error),
    it returns None so callers can fall back to mock responses.

For QA Engineers:
    Mock ``call_llm`` in tests to avoid requiring a running gateway.
    Test both success and failure paths (returns None on error).

For Project Managers:
    The LLM Gateway centralizes all AI costs and provides caching.
    ShopChat calls it for every chat response instead of calling
    the Anthropic API directly.

For End Users:
    The AI responses in your chatbot are powered by this integration.
    Response quality depends on the knowledge base content you provide.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def call_llm(
    prompt: str,
    system: str = "",
    user_id: str = "",
    task_type: str = "chat",
    max_tokens: int = 1000,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> dict | None:
    """
    Call the LLM Gateway to generate an AI completion.

    Sends a POST request to the gateway's /api/v1/generate endpoint
    with the ShopChat service key for authentication.

    Args:
        prompt: The user message or prompt text to send to the LLM.
        system: Optional system instruction for guiding the AI response.
        user_id: The requesting user's ID for cost tracking.
        task_type: Task label for analytics (e.g. 'chat', 'search', 'summary').
        max_tokens: Maximum output tokens (1-8000).
        temperature: Sampling temperature (0.0-2.0). Lower = more deterministic.
        json_mode: Whether to request structured JSON output from the LLM.

    Returns:
        Dict with 'content', 'provider', 'model', 'input_tokens',
        'output_tokens', 'cost_usd', 'cached', 'latency_ms' on success.
        None on any error (network, auth, gateway failure).
    """
    url = f"{settings.llm_gateway_url}/api/v1/generate"
    headers = {"X-Service-Key": settings.llm_gateway_key}
    payload = {
        "user_id": user_id,
        "service": "shopchat",
        "task_type": task_type,
        "prompt": prompt,
        "system": system,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "json_mode": json_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return response.json()

        logger.warning(
            "LLM Gateway returned status %d: %s",
            response.status_code,
            response.text[:200],
        )
        return None

    except httpx.HTTPError as exc:
        logger.warning("LLM Gateway request failed: %s", str(exc))
        return None
    except Exception as exc:
        logger.error("Unexpected error calling LLM Gateway: %s", str(exc))
        return None
