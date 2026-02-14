"""
Health check endpoint.

Provides a simple health check for load balancers, monitoring, and
service discovery.

For Developers:
    Returns service name, status, and current timestamp.
    Can be extended to check database and Redis connectivity.

For QA Engineers:
    GET /health should always return 200 with status 'ok'.
"""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Service health check endpoint.

    Returns:
        Dict with service name, status, and timestamp.
    """
    return {
        "service": settings.service_name,
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }
