"""
PostPilot — FastAPI Application Entry Point.

Initializes the FastAPI app, registers middleware, mounts all API routers,
and configures Stripe pricing at startup.

For Developers:
    Add new routers in the 'Include routers' section. Service-specific
    routers go after the template routers (auth, billing, etc.).

For QA Engineers:
    The app starts with `uvicorn app.main:app --reload`.
    API docs available at /docs (Swagger UI) and /redoc.

For Project Managers:
    This is the main server entry point. All API endpoints are registered here.

For End Users:
    Access the API at http://localhost:8106/api/v1/
    Interactive docs at http://localhost:8106/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.constants.plans import init_price_ids


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle handler.

    Initializes Stripe price IDs on startup from environment configuration.
    """
    # Initialize Stripe price IDs
    init_price_ids(
        pro_price_id=settings.stripe_pro_price_id,
        enterprise_price_id=settings.stripe_enterprise_price_id,
    )
    yield


app = FastAPI(
    title=f"{settings.service_display_name} API",
    description=f"REST API for {settings.service_display_name} — Social Media Automation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include template routers (auth, billing, health, API keys, usage, webhooks)
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.billing import router as billing_router
from app.api.webhooks import router as webhooks_router
from app.api.api_keys import router as api_keys_router
from app.api.usage import router as usage_router

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(usage_router, prefix="/api/v1")

# ── Service-specific routers ────────────────────────────────────────
# Feature-specific routers for PostPilot social media automation.
from app.api.accounts import router as accounts_router
from app.api.posts import router as posts_router
from app.api.queue import router as queue_router
from app.api.analytics import router as analytics_router

app.include_router(accounts_router, prefix="/api/v1")
app.include_router(posts_router, prefix="/api/v1")
app.include_router(queue_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
