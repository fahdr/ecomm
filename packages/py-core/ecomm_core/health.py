"""
Health check router factory and detailed health check utilities.

Creates a standard health check endpoint for any ecomm service, with
an optional detailed mode that probes database and Redis connectivity.

For Developers:
    Use ``create_health_router(service_name)`` for the basic /health endpoint.
    Use ``detailed_health_check(db_session, redis_client, service_name)`` for
    a deeper probe that verifies backend dependencies are reachable.

For QA Engineers:
    GET /health should always return 200 with status 'ok' or 'healthy'.
    GET /health/detail (when wired) returns per-dependency status and may
    report 'degraded' if a backend is unreachable.

For Project Managers:
    Detailed health checks enable load balancers and monitoring systems
    to detect partial outages (e.g. database down but Redis up) and route
    traffic away from degraded instances.

For End Users:
    Health endpoints are used by the platform's monitoring infrastructure.
    They have no direct impact on your experience.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

logger = logging.getLogger(__name__)


def create_health_router(service_name: str) -> APIRouter:
    """
    Create a health check router for the given service.

    Args:
        service_name: The service identifier to include in the response.

    Returns:
        APIRouter with a GET /health endpoint.
    """
    router = APIRouter(tags=["health"])

    @router.get("/health")
    async def health_check():
        """
        Service health check endpoint.

        Returns:
            Dict with service name, status, and timestamp.
        """
        return {
            "service": service_name,
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return router


async def detailed_health_check(
    db_session,
    redis_client=None,
    service_name: str = "service",
) -> dict[str, Any]:
    """
    Perform a detailed health check probing database and Redis connectivity.

    Executes a lightweight query against PostgreSQL and pings Redis (if
    configured). Returns a structured result that monitoring systems can
    parse to determine whether the service is fully healthy or degraded.

    Args:
        db_session: An async SQLAlchemy session to test database connectivity.
            The caller is responsible for session lifecycle management.
        redis_client: An optional async Redis client (e.g. ``aioredis``).
            Pass ``None`` if the service does not use Redis.
        service_name: Identifier for the service in the response payload.

    Returns:
        A dict with the following structure::

            {
                "status": "healthy" | "degraded",
                "service": "<service_name>",
                "timestamp": "<ISO 8601>",
                "checks": {
                    "database": "connected" | "disconnected",
                    "redis": "connected" | "disconnected" | "not_configured",
                }
            }
    """
    result: dict[str, Any] = {
        "status": "healthy",
        "service": service_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {
            "database": "connected",
            "redis": "not_configured",
        },
    }

    # Probe database
    try:
        await db_session.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Health check: database probe failed for %s", service_name)
        result["checks"]["database"] = "disconnected"
        result["status"] = "degraded"

    # Probe Redis
    if redis_client is not None:
        try:
            await redis_client.ping()
            result["checks"]["redis"] = "connected"
        except Exception:
            logger.warning("Health check: Redis probe failed for %s", service_name)
            result["checks"]["redis"] = "disconnected"
            result["status"] = "degraded"

    return result
