"""
Health check router factory.

Creates a standard health check endpoint for any ecomm service.

For Developers:
    Use `create_health_router(service_name)` to add a /health endpoint.

For QA Engineers:
    GET /health should always return 200 with status 'ok'.
"""

from datetime import UTC, datetime

from fastapi import APIRouter


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
