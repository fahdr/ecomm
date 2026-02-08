"""FastAPI application entry point.

Creates the FastAPI app instance, configures CORS middleware,
and registers all API routers for the dropshipping platform.
All versioned endpoints are mounted under the /api/v1 prefix.

**Router Registration Order:**
    1. Infrastructure: health, auth, webhooks (Stripe)
    2. Core resources: stores, products, orders, public
    3. Commerce: subscriptions, discounts, categories, suppliers
    4. Customer experience: reviews, search, upsells, gift cards
    5. Operations: refunds, analytics, tax, segments, bulk
    6. Platform: teams, notifications, domains, store webhooks
    7. Advanced: ab tests, fraud, currency
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Infrastructure routers ---
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.webhooks import router as webhooks_router

# --- Core resource routers ---
from app.api.stores import router as stores_router
from app.api.products import router as products_router
from app.api.orders import router as orders_router
from app.api.public import router as public_router
from app.api.subscriptions import router as subscriptions_router

# --- Phase 1 feature routers (F8-F31) ---
from app.api.discounts import router as discounts_router
from app.api.categories import router as categories_router
from app.api.suppliers import router as suppliers_router
from app.api.reviews import router as reviews_router
from app.api.refunds import router as refunds_router
from app.api.analytics import router as analytics_router
from app.api.tax import router as tax_router
from app.api.upsells import router as upsells_router
from app.api.segments import router as segments_router
from app.api.gift_cards import router as gift_cards_router
from app.api.teams import router as teams_router
from app.api.notifications import router as notifications_router
from app.api.search import router as search_router
from app.api.store_webhooks import router as store_webhooks_router
from app.api.domains import router as domains_router
from app.api.ab_tests import router as ab_tests_router
from app.api.fraud import router as fraud_router
from app.api.bulk import router as bulk_router
from app.api.currency import router as currency_router

from app.config import settings
from app.constants.plans import init_price_ids

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Infrastructure ---
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")

# --- Core resources ---
app.include_router(stores_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
app.include_router(subscriptions_router, prefix="/api/v1")

# --- Phase 1: Commerce features ---
app.include_router(discounts_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(suppliers_router, prefix="/api/v1")

# --- Phase 1: Customer experience ---
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(upsells_router, prefix="/api/v1")
app.include_router(gift_cards_router, prefix="/api/v1")

# --- Phase 1: Operations ---
app.include_router(refunds_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(tax_router, prefix="/api/v1")
app.include_router(segments_router, prefix="/api/v1")
app.include_router(bulk_router, prefix="/api/v1")

# --- Phase 1: Platform management ---
app.include_router(teams_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(domains_router, prefix="/api/v1")
app.include_router(store_webhooks_router, prefix="/api/v1")

# --- Phase 1: Advanced features ---
app.include_router(ab_tests_router, prefix="/api/v1")
app.include_router(fraud_router, prefix="/api/v1")
app.include_router(currency_router, prefix="/api/v1")

# Inject Stripe Price IDs into plan constants at startup.
init_price_ids(
    starter_price_id=settings.stripe_starter_price_id,
    growth_price_id=settings.stripe_growth_price_id,
    pro_price_id=settings.stripe_pro_price_id,
)


@app.get("/")
async def root():
    """Root endpoint returning API information.

    Returns:
        dict: A welcome message and a link to the API documentation.
    """
    return {"message": "Dropshipping Platform API", "docs": "/docs"}
