# Setup Guide

> Part of [ecomm_core](README.md) documentation

This guide covers installation, configuration, and integration of `ecomm_core` into an ecomm SaaS service.

## Installation

### From Monorepo Root

```bash
# Editable install (changes reflect immediately)
pip install -e packages/py-core

# With dev dependencies (pytest, httpx)
pip install -e "packages/py-core[dev]"
```

### In Service Requirements

Add to your service's `requirements.txt`:

```txt
# Local editable install
-e ../../../packages/py-core
```

## Dependencies

`ecomm_core` requires these packages (automatically installed):

- `fastapi>=0.110` — Web framework
- `sqlalchemy[asyncio]>=2.0` — ORM with async support
- `asyncpg>=0.29` — PostgreSQL async driver
- `pydantic>=2.0` — Data validation
- `pydantic-settings>=2.0` — Settings management
- `python-jose[cryptography]>=3.3` — JWT tokens
- `bcrypt>=4.0` — Password hashing
- `email-validator>=2.0` — Email validation
- `httpx>=0.27` — HTTP client for LLM Gateway

## Service Integration Pattern

### 1. Config (`app/config.py`)

Subclass `BaseServiceConfig` and add service-specific settings:

```python
from ecomm_core.config import BaseServiceConfig

class Settings(BaseServiceConfig):
    service_name: str = "trendscout"
    service_display_name: str = "TrendScout"
    service_port: int = 8001

    # BaseServiceConfig provides:
    # - database_url, redis_url
    # - jwt_secret_key, jwt_algorithm
    # - stripe_secret_key, stripe_price_ids
    # - cors_origins, llm_gateway_url

settings = Settings()
```

### 2. Database (`app/database.py`)

Use `ecomm_core.db` utilities to create engine and session factory:

```python
from sqlalchemy import event
from ecomm_core.db import create_db_engine, create_session_factory, create_get_db
from app.config import settings

engine = create_db_engine(settings.database_url, echo=settings.debug)
SessionFactory = create_session_factory(engine)
get_db = create_get_db(SessionFactory)

# Set schema search path for test isolation
@event.listens_for(engine.sync_engine, "connect")
def set_search_path(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute(f"SET search_path TO {settings.service_name}, public")
    cursor.close()
```

### 3. Models (`app/models/__init__.py`)

Import base models and extend as needed:

```python
from ecomm_core.models import Base, User, PlanTier, ApiKey, Subscription, SubscriptionStatus

# Define service-specific models
class ResearchRun(Base):
    __tablename__ = "research_runs"
    # ... your fields
```

### 4. Dependencies (`app/api/deps.py`)

Create auth dependency instances bound to your service:

```python
from ecomm_core.auth.deps import create_get_current_user, create_get_current_user_or_api_key
from app.database import get_db

get_current_user = create_get_current_user(get_db)
get_current_user_or_api_key = create_get_current_user_or_api_key(get_db)
```

### 5. Plans (`app/constants/plans.py`)

Define plan limits with service-specific metrics:

```python
from ecomm_core.models import PlanTier
from ecomm_core.plans import create_default_plan_limits, init_price_ids
from app.config import settings

PLAN_LIMITS = create_default_plan_limits(
    free_items=10,        # e.g., 10 research runs
    free_secondary=25,    # e.g., 25 trend reports
    pro_items=100,
    pro_secondary=500,
)

# Set Stripe price IDs from settings
PLAN_LIMITS = init_price_ids(
    PLAN_LIMITS,
    pro_price_id=settings.stripe_pro_price_id,
    enterprise_price_id=settings.stripe_enterprise_price_id,
)
```

### 6. Routers (`app/main.py`)

Mount shared routers and custom endpoints:

```python
from fastapi import FastAPI
from ecomm_core.auth.router import create_auth_router
from ecomm_core.billing.router import create_billing_router
from ecomm_core.billing.webhooks import create_webhook_router
from ecomm_core.api_keys_router import create_api_keys_router
from ecomm_core.usage_router import create_usage_router
from ecomm_core.health import create_health_router
from ecomm_core.middleware import setup_cors
from app.config import settings
from app.database import get_db, SessionFactory
from app.api.deps import get_current_user, get_current_user_or_api_key
from app.constants.plans import PLAN_LIMITS
from app.services.billing_service import get_usage

app = FastAPI(title=settings.service_display_name)

# Middleware
setup_cors(app, settings.cors_origins_list)

# Health check
app.include_router(create_health_router(settings.service_name))

# Auth
auth_router = create_auth_router(get_db, get_current_user, get_current_user_or_api_key)
app.include_router(auth_router, prefix="/api/v1")

# Billing
billing_router = create_billing_router(get_db, get_current_user, PLAN_LIMITS)
app.include_router(billing_router, prefix="/api/v1")

# Webhooks (Stripe)
webhook_router = create_webhook_router(SessionFactory, PLAN_LIMITS)
app.include_router(webhook_router, prefix="/api/v1")

# API Keys
api_keys_router = create_api_keys_router(get_db, get_current_user)
app.include_router(api_keys_router, prefix="/api/v1")

# Usage reporting
usage_router = create_usage_router(get_db, get_current_user_or_api_key, get_usage)
app.include_router(usage_router, prefix="/api/v1")

# Service-specific routes
# from app.api.research import router as research_router
# app.include_router(research_router, prefix="/api/v1")
```

## Environment Variables

Configure via `.env` file at service root:

```bash
# Service identity
SERVICE_NAME=trendscout
SERVICE_DISPLAY_NAME=TrendScout
SERVICE_PORT=8001

# Database
DATABASE_URL=postgresql+asyncpg://dropship:dropship_dev@db:5432/dropshipping
DATABASE_URL_SYNC=postgresql://dropship:dropship_dev@db:5432/dropshipping

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# JWT (rotate in production!)
JWT_SECRET_KEY=dev-secret-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Stripe (empty = mock mode)
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRO_PRICE_ID=
STRIPE_ENTERPRISE_PRICE_ID=
STRIPE_BILLING_SUCCESS_URL=http://localhost:3001/billing?success=true
STRIPE_BILLING_CANCEL_URL=http://localhost:3001/billing?canceled=true

# LLM Gateway
LLM_GATEWAY_URL=http://llm-gateway:8200
LLM_GATEWAY_KEY=dev-gateway-key
```

## Testing Setup

In your service's `tests/conftest.py`:

```python
import pytest
from ecomm_core.testing import register_and_login
from app.main import app
from app.database import engine, SessionFactory
from app.models import Base

@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(create_tables):
    async with SessionFactory() as session:
        yield session

@pytest.fixture
async def client(create_tables):
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_headers(client):
    return await register_and_login(client)
```

## Verification

Test that the integration works:

```bash
# Start service
uvicorn app.main:app --reload --port 8001

# Test health endpoint
curl http://localhost:8001/health

# Test auth registration
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'

# Run tests
pytest tests/
```

---

*See also: [README](README.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
