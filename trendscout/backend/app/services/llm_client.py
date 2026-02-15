"""
LLM Gateway HTTP client for TrendScout.

Provides a thin async wrapper around the centralized LLM Gateway service.
All AI-powered features (product analysis, opportunity scoring, marketing
angle generation) route through this client rather than calling Claude
directly, enabling centralized rate limiting, caching, and cost tracking.

For Developers:
    ``call_llm`` is the single entry point.  It sends a JSON payload to
    the gateway's ``/api/v1/chat`` endpoint with the ``X-Service-Key``
    header for service-to-service authentication.

    The function returns the parsed JSON response dict.  On any network
    or HTTP error the function raises ``LLMGatewayError`` so callers
    can fall back to mock analysis gracefully.

For Project Managers:
    Routing through the gateway lets the platform team monitor token
    usage, enforce per-service quotas, and add response caching without
    changing individual services.

For QA Engineers:
    In tests, mock ``httpx.AsyncClient.post`` to avoid real HTTP calls.
    Verify that ``LLMGatewayError`` is raised on non-2xx responses
    and on connection timeouts.

For End Users:
    AI analysis in your research results is powered by this gateway.
    If the AI service is temporarily unavailable, results will still
    include scoring data — only the narrative analysis is omitted.
"""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMGatewayError(Exception):
    """
    Raised when the LLM Gateway returns a non-success response or is unreachable.

    Attributes:
        status_code: HTTP status code from the gateway (None if connection failed).
        detail: Human-readable error description.
    """

    def __init__(self, detail: str, status_code: int | None = None):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def call_llm(
    prompt: str,
    system: str = "",
    user_id: str = "",
    task_type: str = "product_analysis",
    *,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 1024,
    temperature: float = 0.3,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Send a prompt to the LLM Gateway and return the parsed response.

    Constructs a chat-completion request, authenticates via
    ``X-Service-Key``, and parses the JSON response body.

    Args:
        prompt: The user-facing prompt text to send.
        system: Optional system prompt for context setting.
        user_id: UUID string of the requesting user (for quota tracking).
        task_type: Classification of the task (e.g. 'product_analysis',
                   'opportunity_scoring').  Used for gateway analytics.
        model: LLM model identifier to request (default: claude-sonnet-4-20250514).
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (lower = more deterministic).
        timeout: HTTP request timeout in seconds.

    Returns:
        Parsed JSON response dict from the gateway.  Typical shape:
        ``{"content": "...", "usage": {"input_tokens": N, "output_tokens": M}}``.

    Raises:
        LLMGatewayError: On connection failure or non-2xx HTTP status.
    """
    url = f"{settings.llm_gateway_url}/api/v1/chat"

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "task_type": task_type,
        "user_id": user_id,
        "messages": [],
    }

    if system:
        payload["messages"].append({"role": "system", "content": system})

    payload["messages"].append({"role": "user", "content": prompt})

    headers = {
        "Content-Type": "application/json",
        "X-Service-Key": settings.llm_gateway_key,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code >= 400:
            detail = f"LLM Gateway returned {response.status_code}: {response.text[:500]}"
            logger.error(detail)
            raise LLMGatewayError(detail, status_code=response.status_code)

        return response.json()

    except httpx.TimeoutException as exc:
        detail = f"LLM Gateway request timed out after {timeout}s: {exc}"
        logger.error(detail)
        raise LLMGatewayError(detail) from exc

    except httpx.ConnectError as exc:
        detail = f"Failed to connect to LLM Gateway at {settings.llm_gateway_url}: {exc}"
        logger.error(detail)
        raise LLMGatewayError(detail) from exc

    except LLMGatewayError:
        raise

    except Exception as exc:
        detail = f"Unexpected error calling LLM Gateway: {exc}"
        logger.error(detail)
        raise LLMGatewayError(detail) from exc
