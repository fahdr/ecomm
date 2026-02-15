"""
LLM Gateway HTTP client for PostPilot.

Provides a thin async wrapper around the centralized LLM Gateway service.
All AI-powered features (caption generation, hashtag suggestions, content
optimization) route through this client rather than calling Claude directly,
enabling centralized rate limiting, caching, and cost tracking.

For Developers:
    ``call_llm`` is the single entry point.  It sends a JSON payload to
    the gateway's ``/api/v1/generate`` endpoint with the ``X-Service-Key``
    header for service-to-service authentication.

    The function returns the parsed JSON response dict.  On any network
    or HTTP error the function raises ``LLMGatewayError`` so callers
    can fall back to mock caption generation gracefully.

For Project Managers:
    Routing through the gateway lets the platform team monitor token
    usage, enforce per-service quotas, and add response caching without
    changing individual services.

For QA Engineers:
    In tests, mock ``call_llm`` to avoid real HTTP calls.
    Verify that ``LLMGatewayError`` is raised on non-2xx responses
    and on connection timeouts.

For End Users:
    AI caption generation in PostPilot is powered by this gateway.
    If the AI service is temporarily unavailable, captions will be
    generated using template-based fallbacks instead.
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
        """
        Initialize the LLMGatewayError.

        Args:
            detail: Human-readable error description.
            status_code: HTTP status code from the gateway (None if connection failed).
        """
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def call_llm(
    prompt: str,
    system: str = "",
    user_id: str = "",
    task_type: str = "caption_generation",
    *,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Send a prompt to the LLM Gateway and return the parsed response.

    Constructs a generate request, authenticates via ``X-Service-Key``,
    and parses the JSON response body.

    Args:
        prompt: The user-facing prompt text to send.
        system: Optional system prompt for context setting.
        user_id: UUID string of the requesting user (for quota tracking).
        task_type: Classification of the task (e.g. 'caption_generation',
                   'hashtag_generation').  Used for gateway analytics.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (higher = more creative).
        timeout: HTTP request timeout in seconds.

    Returns:
        Parsed JSON response dict from the gateway.  Typical shape:
        ``{"content": "...", "provider": "...", "model": "...",
          "input_tokens": N, "output_tokens": M, "cost_usd": 0.001}``.

    Raises:
        LLMGatewayError: On connection failure or non-2xx HTTP status.
    """
    url = f"{settings.llm_gateway_url}/api/v1/generate"

    payload = {
        "user_id": user_id,
        "service": settings.service_name,
        "task_type": task_type,
        "prompt": prompt,
        "system": system,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

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
