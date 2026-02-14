"""
Super Admin Dashboard backend — centralized platform management service.

Provides admin-only APIs for managing the entire ecomm platform, including
health monitoring, LLM Gateway proxy, and service oversight. All routes
are mounted under ``/api/v1/admin/``.

For Developers:
    This is the FastAPI application entry point. Routers are organized by
    domain: ``auth`` for admin authentication, ``health_monitor`` for service
    pings, ``llm_proxy`` for gateway management, and ``services_overview``
    for the service listing.

    Start with: ``uvicorn app.main:app --host 0.0.0.0 --port 8300``

For QA Engineers:
    Hit ``/api/v1/health`` to verify the service is running.
    All ``/api/v1/admin/`` endpoints require JWT authentication,
    except ``/auth/setup`` (first admin) and ``/auth/login``.

For Project Managers:
    The Super Admin Dashboard is the single control plane for the ecomm
    platform. It consolidates health monitoring, LLM management, and
    service oversight into one authenticated interface.

For End Users:
    This service is invisible to end users. It is used by platform
    administrators to keep all ecomm services running smoothly.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health_monitor, llm_proxy, services_overview
from app.config import settings

app = FastAPI(
    title="Super Admin Dashboard",
    description="Centralized platform management service for ecomm",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all admin routers under /api/v1/admin
app.include_router(
    auth.router, prefix="/api/v1/admin", tags=["auth"]
)
app.include_router(
    health_monitor.router, prefix="/api/v1/admin", tags=["health"]
)
app.include_router(
    llm_proxy.router, prefix="/api/v1/admin", tags=["llm"]
)
app.include_router(
    services_overview.router, prefix="/api/v1/admin", tags=["services"]
)


@app.get("/api/v1/health")
async def health_check():
    """
    Basic health check for the admin service.

    Returns:
        Service status with the service name.
    """
    return {
        "status": "healthy",
        "service": settings.service_name,
    }


@app.on_event("startup")
async def startup():
    """
    Create admin database tables on startup.

    Uses SQLAlchemy's ``create_all`` with ``checkfirst=True`` so existing
    tables are not modified. Imports all model modules to register them
    with the Base metadata.
    """
    from app.database import Base, engine
    from app.models import admin_user, health_snapshot  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
