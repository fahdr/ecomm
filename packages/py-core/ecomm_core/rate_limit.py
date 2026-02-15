"""
Rate limiting utilities for all ecomm SaaS services.

Provides ``setup_rate_limiting()`` to attach slowapi-based rate limiting
to a FastAPI application, and ``get_limiter()`` to retrieve the limiter
instance for applying per-route decorators.

For Developers:
    Call ``setup_rate_limiting(app)`` in your service's ``main.py`` after
    creating the FastAPI instance. The limiter is stored on ``app.state``
    so route handlers can import it or access it through the request.

    To apply a custom limit to a specific endpoint::

        from slowapi import Limiter
        from slowapi.util import get_remote_address

        @router.post("/expensive")
        @limiter.limit("10/minute")
        async def expensive_op(request: Request):
            ...

For QA Engineers:
    The default limit is 100 requests per minute per IP. Auth endpoints
    (login, register) are stricter at 5 per minute. Exceeding the limit
    returns HTTP 429 (Too Many Requests).

For Project Managers:
    Rate limiting prevents abuse and ensures fair usage across tenants.
    Limits are configurable per route and per deployment environment.

For End Users:
    If you receive a "Too Many Requests" error, wait a moment and retry.
    This limit protects the platform from excessive automated traffic.
"""

import logging

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def setup_rate_limiting(
    app: FastAPI,
    default_limit: str = "100/minute",
) -> Limiter:
    """
    Attach slowapi rate limiting to a FastAPI application.

    Creates a ``Limiter`` keyed by the caller's remote IP address, stores
    it on ``app.state.limiter``, and registers the 429 error handler.

    Args:
        app: The FastAPI application instance to protect.
        default_limit: Default rate limit applied to all routes unless
            overridden per-route (e.g. ``"100/minute"``, ``"50/hour"``).

    Returns:
        The configured ``Limiter`` instance, which can be used as a
        decorator on individual route handlers for custom limits.
    """
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[default_limit],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    logger.info(
        "Rate limiting enabled with default limit: %s",
        default_limit,
    )

    return limiter


def get_limiter(app: FastAPI) -> Limiter:
    """
    Retrieve the rate limiter from the application state.

    Convenience accessor for route modules that need to apply custom
    per-endpoint limits.

    Args:
        app: The FastAPI application instance.

    Returns:
        The ``Limiter`` instance attached by ``setup_rate_limiting()``.

    Raises:
        AttributeError: If ``setup_rate_limiting()`` was not called first.
    """
    return app.state.limiter
