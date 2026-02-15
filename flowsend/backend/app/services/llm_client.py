"""
LLM Gateway client for FlowSend AI-powered email features.

Wraps the shared ecomm_core LLM client with FlowSend-specific defaults
(service name, task types). Used for AI subject line generation,
content suggestions, and smart segmentation.

For Developers:
    Call ``call_llm()`` for real gateway requests or ``call_llm_mock()``
    during development. Both return the same response shape.

For QA Engineers:
    Always mock LLM calls in tests to avoid external dependencies.
    Use ``call_llm_mock()`` or patch ``call_llm``.

For Project Managers:
    AI features (subject line suggestions, content generation) flow
    through the centralized LLM Gateway for cost tracking and billing.

For End Users:
    AI-powered features help you write better emails and find the
    right audience segments automatically.
"""

from ecomm_core.llm_client import call_llm as _core_call_llm
from ecomm_core.llm_client import call_llm_mock

from app.config import settings


async def call_llm(
    prompt: str,
    *,
    system: str = "",
    user_id: str = "",
    task_type: str = "email_content",
    max_tokens: int = 1000,
    temperature: float = 0.7,
    json_mode: bool = False,
    timeout: float = 60.0,
) -> dict:
    """
    Call the LLM Gateway with FlowSend-specific defaults.

    Delegates to ecomm_core's ``call_llm`` but pre-fills service_name,
    gateway_url, and gateway_key from FlowSend settings.

    Args:
        prompt: The user/task prompt describing what to generate.
        system: System prompt for AI context (e.g., "You are an email copywriter").
        user_id: The end user's UUID for per-customer cost tracking.
        task_type: Task category. Common values for FlowSend:
            - "email_content": Generate email body copy.
            - "subject_line": Generate subject line suggestions.
            - "segmentation": AI-driven segment recommendations.
            - "general": Catch-all for other tasks.
        max_tokens: Maximum tokens in the AI response.
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
        json_mode: Request structured JSON output from the model.
        timeout: HTTP request timeout in seconds.

    Returns:
        Dict with keys: 'content', 'provider', 'model', 'input_tokens',
        'output_tokens', 'cost_usd', 'cached', 'latency_ms'.

    Raises:
        httpx.HTTPStatusError: If the LLM Gateway returns an error.
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


__all__ = ["call_llm", "call_llm_mock"]
