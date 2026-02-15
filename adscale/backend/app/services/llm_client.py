"""
LLM Gateway HTTP client for AdScale.

Provides a thin async wrapper around the centralized LLM Gateway service.
All AI-powered features (ad copy generation, targeting suggestions, campaign
optimization) route through this client rather than calling Claude directly,
enabling centralized rate limiting, caching, and cost tracking.

For Developers:
    ``call_llm`` is the single entry point.  It sends a JSON payload to
    the gateway's ``/api/v1/generate`` endpoint with the ``X-Service-Key``
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
    AI-generated ad copy in your campaigns is powered by this gateway.
    If the AI service is temporarily unavailable, the system will fall
    back to template-based copy generation.
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
    task_type: str = "ad_copy_generation",
    *,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    json_mode: bool = False,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Send a prompt to the LLM Gateway and return the parsed response.

    Constructs a generation request, authenticates via ``X-Service-Key``,
    and parses the JSON response body.

    Args:
        prompt: The user-facing prompt text to send.
        system: Optional system prompt for context setting.
        user_id: UUID string of the requesting user (for quota tracking).
        task_type: Classification of the task (e.g. 'ad_copy_generation',
                   'targeting_suggestion').  Used for gateway analytics.
        max_tokens: Maximum tokens in the response (default 1024).
        temperature: Sampling temperature (0.0-2.0, default 0.7).
        json_mode: Whether to request structured JSON output (default False).
        timeout: HTTP request timeout in seconds (default 30.0).

    Returns:
        Parsed JSON response dict from the gateway.  Typical shape::

            {
                "content": "...",
                "provider": "claude",
                "model": "claude-sonnet-4-20250514",
                "input_tokens": N,
                "output_tokens": M,
                "cost_usd": 0.001,
                "cached": false,
                "latency_ms": 500
            }

    Raises:
        LLMGatewayError: On connection failure or non-2xx HTTP status.
    """
    url = f"{settings.llm_gateway_url}/api/v1/generate"

    payload: dict[str, Any] = {
        "user_id": user_id,
        "service": "adscale",
        "task_type": task_type,
        "prompt": prompt,
        "system": system,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "json_mode": json_mode,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Service-Key": settings.llm_gateway_key,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code >= 400:
            detail = (
                f"LLM Gateway returned {response.status_code}: "
                f"{response.text[:500]}"
            )
            logger.error(detail)
            raise LLMGatewayError(detail, status_code=response.status_code)

        return response.json()

    except httpx.TimeoutException as exc:
        detail = f"LLM Gateway request timed out after {timeout}s: {exc}"
        logger.error(detail)
        raise LLMGatewayError(detail) from exc

    except httpx.ConnectError as exc:
        detail = (
            f"Failed to connect to LLM Gateway at "
            f"{settings.llm_gateway_url}: {exc}"
        )
        logger.error(detail)
        raise LLMGatewayError(detail) from exc

    except LLMGatewayError:
        raise

    except Exception as exc:
        detail = f"Unexpected error calling LLM Gateway: {exc}"
        logger.error(detail)
        raise LLMGatewayError(detail) from exc
