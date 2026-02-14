"""
LLM Gateway client for ContentForge content generation.

Wraps the shared ecomm_core.llm_client with ContentForge-specific defaults
for service name, task types, and gateway configuration.

For Developers:
    Use ``call_contentforge_llm()`` in content generation services instead
    of calling the gateway directly. This function pre-fills the service
    name, gateway URL, and authentication key from ContentForge settings.

    For tests, use ``call_contentforge_llm_mock()`` which returns
    deterministic responses without making HTTP calls.

For QA Engineers:
    In test mode, mock ``app.services.llm_client.call_contentforge_llm``
    to return controlled responses. The mock helper function
    ``call_contentforge_llm_mock`` is provided for convenience.

For Project Managers:
    All AI content generation costs flow through the centralized LLM
    Gateway. This enables per-customer cost tracking and ensures consistent
    billing across all services in the platform.

For End Users:
    When you generate product content, ContentForge sends your product
    data to our AI engine. The generated content is optimized for SEO,
    readability, and conversion based on your selected template.
"""

from ecomm_core.llm_client import call_llm, call_llm_mock

from app.config import settings


async def call_contentforge_llm(
    prompt: str,
    *,
    system: str = "",
    user_id: str = "",
    task_type: str = "content_generation",
    max_tokens: int = 1500,
    temperature: float = 0.7,
    json_mode: bool = False,
    timeout: float = 60.0,
) -> dict:
    """
    Call the LLM Gateway with ContentForge-specific defaults.

    Pre-fills the service name, gateway URL, and authentication key from
    the ContentForge settings so callers do not need to pass them.

    Args:
        prompt: The user/task prompt describing what content to generate.
        system: System prompt providing context and formatting instructions.
        user_id: The end user's UUID string (for per-customer cost tracking).
        task_type: Task category for the gateway — defaults to
            'content_generation'. Other useful values: 'seo_optimization',
            'ab_testing', 'bulk_generation'.
        max_tokens: Maximum tokens in the response (default 1500).
        temperature: Sampling temperature 0.0-1.0 (default 0.7).
        json_mode: Whether to request JSON-formatted output from the LLM.
        timeout: Request timeout in seconds (default 60).

    Returns:
        Dict with keys: 'content', 'provider', 'model', 'input_tokens',
        'output_tokens', 'cost_usd', 'cached', 'latency_ms'.

    Raises:
        httpx.HTTPStatusError: If the LLM gateway returns an error response.
        httpx.ConnectError: If the gateway is unreachable.
    """
    return await call_llm(
        prompt,
        system=system,
        user_id=user_id,
        service_name=settings.service_name,
        task_type=task_type,
        max_tokens=max_tokens,
        temperature=temperature,
        json_mode=json_mode,
        gateway_url=settings.llm_gateway_url,
        gateway_key=settings.llm_gateway_key,
        timeout=timeout,
    )


async def call_contentforge_llm_mock(
    prompt: str,
    *,
    content: str = "Mock LLM response for ContentForge testing.",
    **kwargs,
) -> dict:
    """
    Mock LLM call for ContentForge testing and development.

    Returns a deterministic response without calling any external service.
    Used in tests to avoid hitting the real LLM gateway.

    Args:
        prompt: The prompt (used for response context but not processed).
        content: The mock response content to return.
        **kwargs: Ignored — accepts same kwargs as call_contentforge_llm
            for API compatibility.

    Returns:
        Dict mimicking the LLM gateway response format with 'content',
        'provider' (set to 'mock'), 'model', token counts, and zero cost.
    """
    return await call_llm_mock(prompt, content=content, **kwargs)
