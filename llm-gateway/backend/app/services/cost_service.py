"""
LLM cost tracking service.

Calculates and logs the estimated cost of each LLM generation request
based on per-provider, per-model token pricing.

For Developers:
    ``PRICING`` maps (provider, model_prefix) to input/output cost per 1M tokens.
    Call ``calculate_cost()`` for a single request, ``log_usage()`` to persist.

For QA Engineers:
    Verify cost calculations for known token counts.
    Check that usage logs are created for every generation.

For Project Managers:
    This powers the cost dashboard. Pricing data is approximate and
    should be updated when providers change their rates.
"""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_log import UsageLog

# Pricing per 1M tokens: { (provider, model_prefix): (input_cost, output_cost) }
PRICING: dict[tuple[str, str], tuple[float, float]] = {
    # Anthropic Claude
    ("claude", "claude-3-5-haiku"): (0.80, 4.00),
    ("claude", "claude-sonnet-4"): (3.00, 15.00),
    ("claude", "claude-opus-4"): (15.00, 75.00),
    # OpenAI
    ("openai", "gpt-4o"): (2.50, 10.00),
    ("openai", "gpt-4o-mini"): (0.15, 0.60),
    ("openai", "gpt-4-turbo"): (10.00, 30.00),
    # Google Gemini
    ("gemini", "gemini-2.0-flash"): (0.10, 0.40),
    ("gemini", "gemini-1.5-pro"): (1.25, 5.00),
    # Meta Llama via Together AI
    ("llama", "meta-llama/Llama-3"): (0.88, 0.88),
    # Mistral
    ("mistral", "mistral-large"): (2.00, 6.00),
    ("mistral", "mistral-small"): (0.10, 0.30),
}


def calculate_cost(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> float:
    """
    Calculate the estimated USD cost for a generation request.

    Matches the model name against known pricing prefixes. Falls back
    to the first matching provider entry if no prefix matches.

    Args:
        provider: Provider name (e.g., "claude").
        model: Full model identifier.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.

    Returns:
        Estimated cost in USD.
    """
    input_cost_per_m = 1.00
    output_cost_per_m = 3.00

    for (p, prefix), (ic, oc) in PRICING.items():
        if p == provider and model.startswith(prefix):
            input_cost_per_m = ic
            output_cost_per_m = oc
            break
    else:
        # Fallback: match by provider only (first entry)
        for (p, _), (ic, oc) in PRICING.items():
            if p == provider:
                input_cost_per_m = ic
                output_cost_per_m = oc
                break

    return (input_tokens * input_cost_per_m + output_tokens * output_cost_per_m) / 1_000_000


async def log_usage(
    db: AsyncSession,
    user_id: str,
    service_name: str,
    task_type: str,
    provider_name: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    latency_ms: int,
    cached: bool = False,
    error: str | None = None,
    prompt_preview: str | None = None,
) -> UsageLog:
    """
    Persist a usage log entry to the database.

    Args:
        db: Database session.
        user_id: Requesting user ID.
        service_name: Calling service.
        task_type: Task label from the caller.
        provider_name: Provider used.
        model_name: Model used.
        input_tokens: Input token count.
        output_tokens: Output token count.
        cost_usd: Estimated cost.
        latency_ms: Request latency.
        cached: Whether the response was from cache.
        error: Error message if failed.
        prompt_preview: First 200 chars of the prompt for debugging.

    Returns:
        The created UsageLog record.
    """
    log = UsageLog(
        user_id=user_id,
        service_name=service_name,
        task_type=task_type,
        provider_name=provider_name,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        cached=cached,
        error=error,
        prompt_preview=prompt_preview[:200] if prompt_preview else None,
    )
    db.add(log)
    await db.flush()
    return log
