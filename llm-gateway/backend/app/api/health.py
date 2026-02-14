"""
Health check endpoint for the LLM Gateway.

Reports the gateway's status and per-provider health.

For Developers:
    ``GET /api/v1/health`` returns the gateway status.
    ``GET /api/v1/health/providers`` checks each enabled provider.

For QA Engineers:
    Verify that health returns 200 and correct service_name.
    Verify that provider health correctly reports disabled providers.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.provider_config import ProviderConfig

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Basic health check.

    Returns:
        Service status with name and database connectivity.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": settings.service_name,
        "database": "connected" if db_ok else "disconnected",
    }


@router.get("/health/providers")
async def provider_health(db: AsyncSession = Depends(get_db)):
    """
    Check health of all configured providers.

    Returns:
        List of providers with their enabled status.
    """
    result = await db.execute(
        select(ProviderConfig).order_by(ProviderConfig.priority)
    )
    providers = result.scalars().all()

    return {
        "providers": [
            {
                "name": p.name,
                "display_name": p.display_name,
                "is_enabled": p.is_enabled,
                "models_count": len(p.models) if isinstance(p.models, list) else 0,
            }
            for p in providers
        ]
    }
