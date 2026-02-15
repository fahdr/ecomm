"""
Redis-based response caching for frequently accessed endpoints.

Provides a ``ResponseCache`` class that can be used as a decorator on FastAPI
route handlers to transparently cache JSON responses in Redis. Cache keys
are computed from the endpoint path and query parameters. Authenticated
requests (those carrying an Authorization header) are never cached, since
they typically return personalized data.

For Developers:
    Instantiate ``ResponseCache`` with a Redis client (or ``None`` for
    a no-op cache), then use the ``cached()`` decorator::

        from redis.asyncio import Redis
        redis_client = Redis.from_url("redis://localhost:6379/0")
        cache = ResponseCache(redis_client, default_ttl=300)

        @app.get("/api/v1/products")
        @cache.cached(ttl=60, key_prefix="products")
        async def list_products(request: Request):
            ...

    The decorator expects the first argument after ``self`` to be a
    ``starlette.requests.Request`` (FastAPI injects this automatically
    when you declare ``request: Request`` in the handler signature).

For QA Engineers:
    - Unauthenticated GET requests are cached; POST/PUT/DELETE are never cached.
    - Cached responses include an ``X-Cache: HIT`` header.
    - Fresh responses include ``X-Cache: MISS``.
    - To bust the cache, call ``cache.invalidate(pattern)`` or wait for TTL.
    - When ``redis_client`` is ``None``, the cache is a transparent no-op.

For Project Managers:
    Response caching reduces database load on read-heavy endpoints (product
    listings, storefront pages, public catalogs). A 5-minute default TTL
    balances freshness with performance gains.

For End Users:
    Frequently visited pages load faster because the server remembers
    recent results instead of re-computing them every time.
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable

from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    Redis-backed response cache for FastAPI endpoints.

    Attributes:
        redis: The async Redis client instance, or ``None`` for a no-op cache.
        default_ttl: Default time-to-live in seconds for cached entries.
    """

    def __init__(self, redis_client: Any | None = None, default_ttl: int = 300):
        """
        Initialize the response cache.

        Args:
            redis_client: An async Redis client (e.g., ``redis.asyncio.Redis``).
                Pass ``None`` to disable caching entirely (no-op mode).
            default_ttl: Default cache TTL in seconds. Defaults to 300 (5 min).
        """
        self.redis = redis_client
        self.default_ttl = default_ttl

    def _build_cache_key(self, prefix: str, path: str, query_string: str) -> str:
        """
        Build a deterministic cache key from the request path and query string.

        The query string is hashed to avoid extremely long Redis keys when
        endpoints accept many filter parameters.

        Args:
            prefix: A namespace prefix for the cache key (e.g., "products").
            path: The URL path of the request.
            query_string: The raw query string (after the ``?``).

        Returns:
            A string suitable for use as a Redis key.
        """
        query_hash = hashlib.md5(query_string.encode()).hexdigest()[:12]
        return f"{prefix}:{path}:{query_hash}"

    def cached(
        self, ttl: int | None = None, key_prefix: str = "cache"
    ) -> Callable:
        """
        Decorator that caches the JSON response of a FastAPI route handler.

        Skips caching when:
            - Redis client is ``None`` (no-op mode).
            - The request method is not GET.
            - The request includes an Authorization header (personalized data).

        Args:
            ttl: Cache TTL in seconds. Falls back to ``self.default_ttl``.
            key_prefix: Prefix for the Redis cache key namespace.

        Returns:
            A decorator function.
        """
        cache_ttl = ttl if ttl is not None else self.default_ttl

        def decorator(func: Callable) -> Callable:
            """
            Wrap the route handler with caching logic.

            Args:
                func: The original route handler coroutine.

            Returns:
                The wrapped coroutine with cache-check-before-execute logic.
            """

            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                """
                Execute the cached route handler.

                Attempts to serve from Redis first. On a miss, calls the
                original handler, stores the result, and returns it.

                Args:
                    *args: Positional arguments passed to the handler.
                    **kwargs: Keyword arguments passed to the handler.

                Returns:
                    The original handler's return value (possibly from cache).
                """
                # No-op if Redis is not configured
                if self.redis is None:
                    return await func(*args, **kwargs)

                # Extract the Request object from args or kwargs
                request: Request | None = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                if request is None:
                    request = kwargs.get("request")

                # Cannot cache without a request object
                if request is None:
                    return await func(*args, **kwargs)

                # Only cache GET requests
                if request.method != "GET":
                    return await func(*args, **kwargs)

                # Skip cache for authenticated requests (personalized data)
                if request.headers.get("authorization"):
                    return await func(*args, **kwargs)

                # Build cache key
                cache_key = self._build_cache_key(
                    key_prefix,
                    request.url.path,
                    str(request.url.query),
                )

                # Check cache
                try:
                    cached_data = await self.redis.get(cache_key)
                    if cached_data is not None:
                        data = json.loads(cached_data)
                        response = JSONResponse(content=data)
                        response.headers["X-Cache"] = "HIT"
                        return response
                except Exception as exc:
                    logger.warning("Cache read failed: %s", exc)

                # Cache miss — call the original handler
                result = await func(*args, **kwargs)

                # Store result in cache
                try:
                    # Handle both dict returns and Response objects
                    if isinstance(result, dict | list):
                        await self.redis.set(
                            cache_key,
                            json.dumps(result),
                            ex=cache_ttl,
                        )
                    elif hasattr(result, "body"):
                        await self.redis.set(
                            cache_key,
                            result.body.decode(),
                            ex=cache_ttl,
                        )
                except Exception as exc:
                    logger.warning("Cache write failed: %s", exc)

                # Add cache miss header if result is a Response
                if hasattr(result, "headers"):
                    result.headers["X-Cache"] = "MISS"

                return result

            return wrapper

        return decorator

    async def invalidate(self, pattern: str) -> int:
        """
        Delete all cache entries matching a key pattern.

        Uses Redis SCAN to find matching keys, then deletes them in a single
        pipeline call for efficiency.

        Args:
            pattern: A Redis key glob pattern (e.g., ``products:*``).

        Returns:
            The number of keys deleted, or 0 if Redis is unavailable.
        """
        if self.redis is None:
            return 0

        deleted = 0
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info("Cache invalidation: deleted %d keys matching '%s'", deleted, pattern)
        except Exception as exc:
            logger.warning("Cache invalidation failed for pattern '%s': %s", pattern, exc)

        return deleted

    async def clear_all(self) -> bool:
        """
        Flush all cached entries from the connected Redis database.

        Use with caution in production. Primarily intended for testing and
        development.

        Returns:
            True if the flush succeeded, False otherwise.
        """
        if self.redis is None:
            return False

        try:
            await self.redis.flushdb()
            logger.info("Cache cleared: all keys flushed")
            return True
        except Exception as exc:
            logger.warning("Cache clear failed: %s", exc)
            return False
