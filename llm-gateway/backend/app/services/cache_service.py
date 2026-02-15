"""
LLM response caching service.

Caches generation results in Redis to avoid duplicate API calls.
The cache key is a hash of (provider, model, prompt, system, temperature, json_mode).

For Developers:
    Uses Redis with configurable TTL. Same prompt from different services
    or users hits the same cache entry (content is the same).
    Set ``cache_ttl_seconds=0`` to disable caching.

For QA Engineers:
    Verify that identical requests return cached=True on second call.
    Verify that different temperatures produce different cache keys.

For Project Managers:
    Caching reduces AI costs by reusing identical responses.
    The hit rate is visible in the admin dashboard.
"""

import hashlib
import json

import redis.asyncio as redis

from app.config import settings
from app.providers.base import GenerationResult


_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    """
    Get or create the Redis client singleton.

    Returns:
        Redis async client.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _make_cache_key(
    provider: str,
    model: str,
    prompt: str,
    system: str,
    temperature: float,
    json_mode: bool,
) -> str:
    """
    Generate a deterministic cache key for a generation request.

    Args:
        provider: Provider name.
        model: Model identifier.
        prompt: The user prompt.
        system: The system message.
        temperature: Sampling temperature.
        json_mode: Whether JSON output was requested.

    Returns:
        Cache key string prefixed with ``llm_cache:``.
    """
    payload = json.dumps(
        {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "system": system,
            "temperature": temperature,
            "json_mode": json_mode,
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"llm_cache:{digest}"


async def get_cached(
    provider: str,
    model: str,
    prompt: str,
    system: str,
    temperature: float,
    json_mode: bool,
) -> GenerationResult | None:
    """
    Look up a cached generation result.

    Args:
        provider: Provider name.
        model: Model identifier.
        prompt: User prompt.
        system: System message.
        temperature: Sampling temperature.
        json_mode: Whether JSON output was requested.

    Returns:
        Cached GenerationResult if found, else None.
    """
    if settings.cache_ttl_seconds <= 0:
        return None

    r = _get_redis()
    key = _make_cache_key(provider, model, prompt, system, temperature, json_mode)
    cached = await r.get(key)
    if cached:
        data = json.loads(cached)
        return GenerationResult(
            content=data["content"],
            input_tokens=data["input_tokens"],
            output_tokens=data["output_tokens"],
            model=data["model"],
            provider=data["provider"],
        )
    return None


async def set_cached(
    provider: str,
    model: str,
    prompt: str,
    system: str,
    temperature: float,
    json_mode: bool,
    result: GenerationResult,
) -> None:
    """
    Store a generation result in cache.

    Args:
        provider: Provider name.
        model: Model identifier.
        prompt: User prompt.
        system: System message.
        temperature: Sampling temperature.
        json_mode: Whether JSON output was requested.
        result: The generation result to cache.
    """
    if settings.cache_ttl_seconds <= 0:
        return

    r = _get_redis()
    key = _make_cache_key(provider, model, prompt, system, temperature, json_mode)
    data = json.dumps({
        "content": result.content,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "model": result.model,
        "provider": result.provider,
    })
    await r.setex(key, settings.cache_ttl_seconds, data)
