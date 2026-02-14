"""
LLM Gateway client for making AI requests from any service.

Provides a simple async function to call the centralized LLM Gateway,
which routes requests to the appropriate provider (Claude, OpenAI, etc.).

For Developers:
    Use `call_llm()` instead of importing LLM SDKs directly.
    The gateway handles provider selection, rate limiting, caching, and cost tracking.

For QA Engineers:
    In test mode, mock this function to return deterministic responses.

For Project Managers:
    All AI costs flow through the gateway, enabling per-customer billing
    and centralized cost monitoring via the admin dashboard.
"""

import httpx


async def call_llm(
    prompt: str,
    *,
    system: str = "",
    user_id: str = "",
    service_name: str = "",
    task_type: str = "general",
    max_tokens: int = 1000,
    temperature: float = 0.7,
    json_mode: bool = False,
    gateway_url: str = "http://localhost:8200",
    gateway_key: str = "",
    timeout: float = 60.0,
) -> dict:
    """
    Call the LLM Gateway to generate AI content.

    Args:
        prompt: The user/task prompt.
        system: System prompt for context.
        user_id: The end user's UUID (for per-customer routing).
        service_name: The calling service (e.g., 'trendscout').
        task_type: Task category (e.g., 'product_analysis', 'content_generation').
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (0.0-1.0).
        json_mode: Whether to request JSON-formatted output.
        gateway_url: LLM Gateway base URL.
        gateway_key: Service authentication key for the gateway.
        timeout: Request timeout in seconds.

    Returns:
        Dict with 'content', 'provider', 'model', 'input_tokens',
        'output_tokens', 'cost_usd', 'cached', 'latency_ms'.

    Raises:
        httpx.HTTPStatusError: If the gateway returns an error response.
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{gateway_url}/api/v1/generate",
            json={
                "user_id": user_id,
                "service": service_name,
                "task_type": task_type,
                "prompt": prompt,
                "system": system,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "json_mode": json_mode,
            },
            headers={"X-Service-Key": gateway_key} if gateway_key else {},
        )
        resp.raise_for_status()
        return resp.json()


async def call_llm_mock(
    prompt: str,
    *,
    content: str = "Mock LLM response for testing.",
    **kwargs,
) -> dict:
    """
    Mock LLM call for testing and development.

    Returns a deterministic response without calling any external service.

    Args:
        prompt: The prompt (used for response context).
        content: The mock response content.
        **kwargs: Ignored (accepts same kwargs as call_llm for compatibility).

    Returns:
        Dict mimicking the gateway response format.
    """
    return {
        "content": content,
        "provider": "mock",
        "model": "mock-v1",
        "input_tokens": len(prompt.split()),
        "output_tokens": len(content.split()),
        "cost_usd": 0.0,
        "cached": False,
        "latency_ms": 1,
    }
