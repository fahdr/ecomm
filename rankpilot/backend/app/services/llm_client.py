"""
LLM Gateway client for the RankPilot SEO engine.

Wraps the shared ecomm_core LLM client with RankPilot-specific defaults
(service name, gateway URL, gateway key). Provides a convenient interface
for SEO-related AI tasks like blog generation and content optimization.

For Developers:
    Use ``call_llm()`` for all AI requests. It automatically injects
    RankPilot's service credentials and gateway URL from settings.
    In tests, mock ``app.services.llm_client.call_llm`` to avoid
    real gateway calls.

For QA Engineers:
    Verify that the client passes the correct headers and payload.
    Use ``call_llm_mock()`` from ecomm_core for deterministic test responses.

For Project Managers:
    All AI costs are routed through the centralized LLM Gateway, enabling
    per-service and per-customer cost tracking and billing.

For End Users:
    AI features like blog generation and content optimization are powered
    by the LLM Gateway. Usage counts toward your plan limits.
"""

from ecomm_core.llm_client import call_llm as _core_call_llm

from app.config import settings


async def call_llm(
    prompt: str,
    *,
    system: str = "",
    user_id: str = "",
    task_type: str = "general",
    max_tokens: int = 1000,
    temperature: float = 0.7,
    json_mode: bool = False,
    timeout: float = 60.0,
) -> dict:
    """
    Call the LLM Gateway with RankPilot-specific defaults.

    Wraps the core ``call_llm`` from ecomm_core, injecting the service name,
    gateway URL, and gateway key from the RankPilot settings.

    Args:
        prompt: The user/task prompt to send to the LLM.
        system: System prompt providing context or instructions.
        user_id: The end user's UUID string (for per-customer routing/billing).
        task_type: Task category (e.g., 'blog_generation', 'seo_optimization').
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
        json_mode: Whether to request JSON-formatted output from the LLM.
        timeout: Request timeout in seconds.

    Returns:
        Dict with 'content', 'provider', 'model', 'input_tokens',
        'output_tokens', 'cost_usd', 'cached', 'latency_ms'.

    Raises:
        httpx.HTTPStatusError: If the gateway returns an error response.
    """
    return await _core_call_llm(
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
