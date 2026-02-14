"""
AdScale — FastAPI Application Entry Point.

Uses shared router factories from ecomm_core for auth, billing, health,
API keys, usage, and webhooks. Service-specific routers are included separately.

For Developers:
    Add new routers in the 'Service-specific routers' section.

For QA Engineers:
    The app starts with ``uvicorn app.main:app --reload``.
    API docs at /docs and /redoc.

For End Users:
    Access the API at http://localhost:8107/api/v1/
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
from ecomm_core.middleware import setup_cors
from ecomm_core.billing.service import get_usage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle handler. Initializes Stripe price IDs on startup."""
    init_price_ids(
        pro_price_id=settings.stripe_pro_price_id,
        enterprise_price_id=settings.stripe_enterprise_price_id,
    )
    yield


app = FastAPI(
    title=f"{settings.service_display_name} API",
    description=f"REST API for {settings.service_display_name} — AI Ad Campaign Manager",
    version="1.0.0",
    lifespan=lifespan,
)

setup_cors(app, settings.cors_origins_list)

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
from app.api.campaigns import router as campaigns_router
from app.api.ad_groups import router as ad_groups_router
from app.api.creatives import router as creatives_router
from app.api.metrics import router as metrics_router
from app.api.rules import router as rules_router
from app.api.connections import router as connections_router
from app.api.tools import router as tools_router
from app.api.webhooks import router as platform_webhooks_router

app.include_router(accounts_router, prefix="/api/v1")
app.include_router(campaigns_router, prefix="/api/v1")
app.include_router(ad_groups_router, prefix="/api/v1")
app.include_router(creatives_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(connections_router, prefix="/api/v1")
app.include_router(tools_router, prefix="/api/v1")
app.include_router(platform_webhooks_router, prefix="/api/v1")
