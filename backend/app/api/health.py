"""Health check router.

Provides a lightweight endpoint for monitoring tools and load balancers
to verify the API and its database connection are operational.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check API and database health.

    Executes a trivial SQL query to confirm the database connection is alive.

    Args:
        db: Async database session injected by FastAPI.

    Returns:
        dict: ``{"status": "ok"}`` when the service is healthy.
    """
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
