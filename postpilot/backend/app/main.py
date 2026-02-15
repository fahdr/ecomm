"""
PostPilot — FastAPI Application Entry Point.

Uses shared router factories from ecomm_core for auth, billing, health,
API keys, usage, and webhooks. Service-specific routers are included separately.

For Developers:
    Add new routers in the 'Service-specific routers' section.

For QA Engineers:
    The app starts with ``uvicorn app.main:app --reload``.
    API docs at /docs and /redoc.

For End Users:
    Access the API at http://localhost:8106/api/v1/
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.constants.plans import PLAN_LIMITS, init_price_ids
from app.database import async_session_factory, get_db

from ecomm_core.auth.deps import create_get_current_user, create_get_current_user_or_api_key
from ecomm_core.auth.router import create_auth_router
from ecomm_core.billing.router import create_billing_router
from ecomm_core.billing.webhooks import create_webhook_router
from ecomm_core.health import create_health_router
from ecomm_core.api_keys_router import create_api_keys_router
from ecomm_core.usage_router import create_usage_router
from ecomm_core.middleware import setup_cors, RequestLoggingMiddleware
from ecomm_core.monitoring import init_sentry
from ecomm_core.rate_limit import setup_rate_limiting
from ecomm_core.security import SecurityHeadersMiddleware
from ecomm_core.billing.service import get_usage

# ── Sentry error tracking ─────────────────────────────────────────
init_sentry(
    service_name=settings.service_name,
    dsn=settings.sentry_dsn,
    environment=settings.environment,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle handler. Initializes Stripe price IDs on startup."""
    init_price_ids(
        PLAN_LIMITS,
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

# Security headers middleware (must be added before CORS)
app.add_middleware(SecurityHeadersMiddleware)

setup_cors(app, settings.cors_origins_list)

# Request logging middleware (adds X-Request-ID and structured access logs)
app.add_middleware(RequestLoggingMiddleware, service_name=settings.service_name)

# Rate limiting (100 requests/minute default)
setup_rate_limiting(app)

get_current_user = create_get_current_user(get_db)
get_current_user_or_api_key = create_get_current_user_or_api_key(get_db)

app.include_router(create_health_router(settings.service_name), prefix="/api/v1")
app.include_router(create_auth_router(get_db, get_current_user, get_current_user_or_api_key), prefix="/api/v1")
app.include_router(create_billing_router(get_db, get_current_user, PLAN_LIMITS), prefix="/api/v1")
app.include_router(create_webhook_router(async_session_factory, PLAN_LIMITS), prefix="/api/v1")
app.include_router(create_api_keys_router(get_db, get_current_user), prefix="/api/v1")
app.include_router(create_usage_router(get_db, get_current_user_or_api_key, lambda db, user: get_usage(db, user, PLAN_LIMITS)), prefix="/api/v1")

# ── Service-specific routers ────────────────────────────────────────
from app.api.accounts import router as accounts_router
from app.api.posts import router as posts_router
from app.api.queue import router as queue_router
from app.api.analytics import router as analytics_router
from app.api.connections import router as connections_router
from app.api.webhooks import router as platform_webhooks_router

app.include_router(accounts_router, prefix="/api/v1")
app.include_router(posts_router, prefix="/api/v1")
app.include_router(queue_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(connections_router, prefix="/api/v1")
app.include_router(platform_webhooks_router, prefix="/api/v1")

# ── AI suggestions ────────────────────────────────────────────────
from app.api.suggestions import router as suggestions_router

app.include_router(suggestions_router, prefix="/api/v1")
