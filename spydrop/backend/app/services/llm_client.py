"""
LLM Gateway client for SpyDrop.

Provides a simple async HTTP client that calls the centralized LLM Gateway
service. All AI-powered features (competitive analysis, source finding,
keyword extraction) route through this client.

For Developers:
    Call ``call_llm(prompt, system, user_id, task_type)`` to get an LLM
    completion. The client sends requests to ``settings.llm_gateway_url``
    with the ``X-Service-Key`` header for authentication.

    The LLM Gateway handles provider routing, caching, rate limiting,
    and cost tracking. This client only needs to send the prompt and
    parse the response.

For QA Engineers:
    Mock ``call_llm`` in tests to avoid hitting the real LLM Gateway.
    Verify that the client handles timeouts, 401, 429, and 5xx errors
    gracefully by returning appropriate error dicts.

For Project Managers:
    All AI costs flow through the centralized LLM Gateway, enabling
    unified cost tracking and usage analytics across all services.

For End Users:
    This powers the AI features in SpyDrop — competitive analysis,
    smart product matching, and market intelligence insights.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Default timeout for LLM Gateway calls (30 seconds).
_DEFAULT_TIMEOUT = 30.0


async def call_llm(
    prompt: str,
    system: str = "",
    user_id: str = "",
    task_type: str = "general",
    *,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    json_mode: bool = False,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict:
    """
    Call the centralized LLM Gateway for a text completion.

    Sends a POST request to the LLM Gateway's ``/api/v1/generate`` endpoint
    with the service authentication key and prompt data. Handles network
    errors, timeouts, and non-200 responses gracefully.

    Args:
        prompt: The user message / prompt text to send to the LLM.
        system: Optional system instruction to guide the LLM's behavior.
        user_id: The requesting customer's user ID for usage tracking.
        task_type: Caller-defined task label for analytics
            (e.g., 'competitive_analysis', 'source_finding').
        max_tokens: Maximum number of output tokens (1-8000).
        temperature: Sampling temperature controlling randomness (0.0-2.0).
        json_mode: Whether to request structured JSON output from the LLM.
        timeout: Request timeout in seconds (default 30).

    Returns:
        A dict with the following keys on success:
            - content (str): The generated text.
            - provider (str): Provider that handled the request.
            - model (str): Model used for generation.
            - input_tokens (int): Input token count.
            - output_tokens (int): Output token count.
            - cost_usd (float): Estimated cost in USD.
            - cached (bool): Whether the response came from cache.
            - latency_ms (int): End-to-end latency in milliseconds.

        On failure, returns a dict with:
            - error (str): Human-readable error description.
            - content (str): Empty string (for safe fallback access).
    """
    url = f"{settings.llm_gateway_url}/api/v1/generate"
    headers = {
        "X-Service-Key": settings.llm_gateway_key,
        "Content-Type": "application/json",
    }
    payload = {
        "user_id": user_id,
        "service": settings.service_name,
        "task_type": task_type,
        "prompt": prompt,
        "system": system,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "json_mode": json_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return response.json()

        # Handle known error codes
        error_detail = ""
        try:
            error_detail = response.json().get("detail", response.text)
        except Exception:
            error_detail = response.text

        if response.status_code == 401:
            logger.error("LLM Gateway authentication failed: invalid service key")
            return {"error": "LLM Gateway authentication failed", "content": ""}

        if response.status_code == 429:
            logger.warning("LLM Gateway rate limit exceeded")
            return {"error": "LLM Gateway rate limit exceeded", "content": ""}

        logger.error(
            "LLM Gateway returned %d: %s", response.status_code, error_detail
        )
        return {
            "error": f"LLM Gateway error ({response.status_code}): {error_detail}",
            "content": "",
        }

    except httpx.TimeoutException:
        logger.error("LLM Gateway request timed out after %.1fs", timeout)
        return {"error": "LLM Gateway request timed out", "content": ""}

    except httpx.ConnectError:
        logger.error("Could not connect to LLM Gateway at %s", url)
        return {"error": "Could not connect to LLM Gateway", "content": ""}

    except Exception as exc:
        logger.exception("Unexpected error calling LLM Gateway: %s", exc)
        return {"error": f"Unexpected LLM Gateway error: {exc}", "content": ""}
