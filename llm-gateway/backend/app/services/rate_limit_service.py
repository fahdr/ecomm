"""
Per-provider rate limiting service.

Uses Redis token bucket algorithm to enforce rate limits on LLM requests.
Each provider has its own bucket with configurable RPM (requests per minute).

For Developers:
    Call ``check_rate_limit()`` before making a provider request. It returns
    True if the request is allowed, False if rate-limited. Uses Redis
    atomic increment with TTL for the sliding window.

For QA Engineers:
    Test that exceeding rate_limit_rpm blocks subsequent requests.
    Verify that the limit resets after the window expires.

For Project Managers:
    Rate limiting prevents hitting provider quotas and keeps costs predictable.
    Limits are configured per-provider in the admin dashboard.
"""

import redis.asyncio as redis

from app.config import settings

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    """
    Get or create the Redis client singleton for rate limiting.

    Returns:
        Redis async client.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def check_rate_limit(provider_name: str, rpm_limit: int) -> bool:
    """
    Check if a request to the given provider is within rate limits.

    Uses a sliding-window counter in Redis. Each key represents one
    minute window for one provider.

    Args:
        provider_name: The provider to check.
        rpm_limit: Maximum requests per minute for this provider.

    Returns:
        True if the request is allowed, False if rate-limited.
    """
    if rpm_limit <= 0:
        return True

    r = _get_redis()
    key = f"llm_rate:{provider_name}"

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, 60)
    results = await pipe.execute()
    current_count = results[0]

    return current_count <= rpm_limit


async def get_remaining(provider_name: str, rpm_limit: int) -> int:
    """
    Get the number of remaining requests in the current window.

    Args:
        provider_name: The provider to check.
        rpm_limit: Maximum requests per minute for this provider.

    Returns:
        Number of remaining allowed requests.
    """
    r = _get_redis()
    key = f"llm_rate:{provider_name}"
    current = await r.get(key)
    used = int(current) if current else 0
    return max(0, rpm_limit - used)
