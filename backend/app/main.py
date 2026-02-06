"""FastAPI application entry point.

Creates the FastAPI app instance and registers all API routers.
All versioned endpoints are mounted under the /api/v1 prefix.
"""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.config import settings

app = FastAPI(title=settings.app_name)

app.include_router(health_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint returning API information.

    Returns:
        dict: A welcome message and a link to the API documentation.
    """
    return {"message": "Dropshipping Platform API", "docs": "/docs"}
