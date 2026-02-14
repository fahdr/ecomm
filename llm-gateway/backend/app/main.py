"""
LLM Gateway microservice — centralized AI inference proxy.

Routes LLM requests from all ecomm services through a single gateway that
handles provider selection, caching, rate limiting, and cost tracking.

For Developers:
    This is the FastAPI application entry point. All routers are mounted
    under /api/v1/. The gateway authenticates callers via X-Service-Key header.

For QA Engineers:
    Start with: ``uvicorn app.main:app --host 0.0.0.0 --port 8200``
    Hit ``/api/v1/health`` to verify the service is running.

For Project Managers:
    The LLM Gateway is the only true microservice in the platform.
    It centralizes AI costs, enables admin control over which AI models
    are used, and prevents each service from bundling 6 SDK dependencies.

For End Users:
    This service is invisible to end users — it works behind the scenes
    to power AI features across all ecomm products.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import generate, health, overrides, providers, usage
from app.config import settings

app = FastAPI(
    title="LLM Gateway",
    description="Centralized AI inference proxy for ecomm services",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(generate.router, prefix="/api/v1", tags=["generate"])
app.include_router(providers.router, prefix="/api/v1/providers", tags=["providers"])
app.include_router(overrides.router, prefix="/api/v1/overrides", tags=["overrides"])
app.include_router(usage.router, prefix="/api/v1/usage", tags=["usage"])


@app.on_event("startup")
async def startup():
    """
    Create database tables on startup.

    Uses SQLAlchemy's create_all with checkfirst=True, so existing
    tables are not modified.
    """
    from app.database import Base, engine
    from app.models import customer_override, provider_config, usage_log  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
