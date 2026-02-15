"""
SourcePilot — FastAPI Application Entry Point.

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
    Access the API at http://localhost:8109/api/v1/
    Interactive docs at http://localhost:8109/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ecomm_core.middleware import RequestLoggingMiddleware
from ecomm_core.monitoring import init_sentry
from ecomm_core.rate_limit import setup_rate_limiting
from ecomm_core.security import SecurityHeadersMiddleware

from app.config import settings
from app.constants.plans import init_price_ids

# ── Sentry error tracking ─────────────────────────────────────────
init_sentry(
    service_name=settings.service_name,
    dsn=settings.sentry_dsn,
    environment=settings.environment,
)


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
    description=f"REST API for {settings.service_display_name} — Automated Supplier Product Import",
    version="1.0.0",
    lifespan=lifespan,
)

# Security headers middleware (must be added before CORS)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware (adds X-Request-ID and structured access logs)
app.add_middleware(RequestLoggingMiddleware, service_name=settings.service_name)

# Rate limiting (100 requests/minute default)
setup_rate_limiting(app)

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
from app.api.imports import router as imports_router
from app.api.suppliers import router as suppliers_router
from app.api.products import router as products_router
from app.api.connections import router as connections_router
from app.api.price_watch import router as price_watch_router

app.include_router(imports_router, prefix="/api/v1")
app.include_router(suppliers_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(connections_router, prefix="/api/v1")
app.include_router(price_watch_router, prefix="/api/v1")

# ── AI suggestions ────────────────────────────────────────────────
from app.api.suggestions import router as suggestions_router

app.include_router(suggestions_router, prefix="/api/v1")
