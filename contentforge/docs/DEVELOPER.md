# Developer Guide

**For Developers:** ContentForge is an independently hostable SaaS product that generates SEO-optimized product titles, descriptions, meta tags, bullet points, and keywords using Claude AI. It also handles product image download, optimization, and format conversion via Pillow. This guide covers everything you need to set up, develop, test, and extend the service.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend API | FastAPI + SQLAlchemy 2.0 (async) | Python 3.12 |
| Database | PostgreSQL | 16 |
| Cache / Queue Broker | Redis | 7 |
| Task Queue | Celery | 5.x |
| Image Processing | Pillow | Latest |
| Dashboard | Next.js (App Router) | 16 |
| Dashboard Styling | Tailwind CSS | 4.x |
| Landing Page | Next.js (static export) | 16 |
| ORM Migrations | Alembic | Latest |
| Testing | pytest + pytest-asyncio + httpx | Latest |

---

## Local Dev Setup

ContentForge runs on three processes locally: the FastAPI backend (port 8102), the Next.js dashboard (port 3102), and the Next.js landing page (port 3202). PostgreSQL and Redis are provided by the devcontainer.

### Quick Start

```bash
make install && make migrate && make start
```

### Access Points

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8102 |
| API Docs (Swagger) | http://localhost:8102/docs |
| Dashboard | http://localhost:3102 |
| Landing Page | http://localhost:3202 |

---

## Services

### Start All Services

```bash
make start
```

### Start Individual Services

```bash
# Backend only
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8102 --reload

# Dashboard only
cd dashboard && npm run dev -- --port 3102

# Landing page only
cd master-landing && npm run dev -- --port 3202

# Celery worker (for async task processing)
cd backend && celery -A app.tasks worker -Q contentforge --loglevel=info
```

### Install Dependencies

```bash
# Backend
cd backend && pip install -r requirements.txt

# Dashboard
cd dashboard && npm install

# Landing
cd master-landing && npm install
```

---

## Ports

| Service | Port | Purpose |
|---------|------|---------|
| Backend API | 8102 | FastAPI REST API |
| Dashboard | 3102 | Next.js admin dashboard |
| Landing Page | 3202 | Next.js marketing site |
| PostgreSQL | 5502 | Database |
| Redis | 6402 | Cache and Celery broker |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://dropship:dropship_dev@db:5502/contentforge` | Async database connection string |
| `DATABASE_URL_SYNC` | `postgresql://dropship:dropship_dev@db:5502/contentforge` | Sync database connection string (for Alembic) |
| `REDIS_URL` | `redis://redis:6402/0` | Redis connection for caching |
| `CELERY_BROKER_URL` | `redis://redis:6402/1` | Celery task broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6402/2` | Celery result backend |
| `SECRET_KEY` | (generated) | JWT signing key |
| `STRIPE_SECRET_KEY` | (empty = mock mode) | Stripe API secret key |
| `STRIPE_WEBHOOK_SECRET` | (empty = mock mode) | Stripe webhook signing secret |
| `STRIPE_PRO_PRICE_ID` | (empty) | Stripe Price ID for Pro tier |
| `STRIPE_ENTERPRISE_PRICE_ID` | (empty) | Stripe Price ID for Enterprise tier |
| `ANTHROPIC_API_KEY` | (empty = mock mode) | Claude AI API key for content generation |

---

## Project Structure

```
services/contentforge/
  backend/
    app/
      api/
        __init__.py            # API route registration
        auth.py                # POST /auth/register, /auth/login, /auth/refresh, /auth/me, /auth/provision
        billing.py             # GET /billing/plans, POST /billing/checkout, /billing/portal, GET /billing/current, /billing/overview
        api_keys.py            # POST /api-keys, GET /api-keys, DELETE /api-keys/{id}
        content.py             # POST /content/generate, /content/generate/bulk, GET /content/jobs, /content/jobs/{id}, DELETE /content/jobs/{id}, PATCH /content/{id}
        templates.py           # POST /templates, GET /templates, /templates/{id}, PATCH /templates/{id}, DELETE /templates/{id}
        images.py              # GET /images, /images/{id}, DELETE /images/{id}
        health.py              # GET /health
        usage.py               # GET /usage
        webhooks.py            # POST /webhooks/stripe
        deps.py                # get_current_user, get_current_user_or_api_key dependencies
      models/
        base.py                # SQLAlchemy declarative base
        user.py                # User model + PlanTier enum
        api_key.py             # ApiKey model (SHA-256 hashed keys)
        subscription.py        # Subscription model + SubscriptionStatus enum
        generation.py          # GenerationJob + GeneratedContent models
        image_job.py           # ImageJob model
        template.py            # Template model (system + custom)
      services/
        auth_service.py        # User registration, login, JWT tokens, API key auth
        content_service.py     # Generation job lifecycle, plan limit checks, mock AI content
        image_service.py       # Image CRUD, mock image processing
        pricing_service.py     # Markup calculation, psychological rounding strategies
        billing_service.py     # Stripe checkout/portal, subscription management, usage metrics
        template_seeder.py     # Seeds system templates at startup
      schemas/
        auth.py                # Request/response schemas for auth endpoints
        content.py             # Schemas for generation jobs, content, images, templates
        billing.py             # Schemas for plans, checkout, subscriptions, usage
      constants/
        plans.py               # PlanLimits dataclass, PLAN_LIMITS dict, Stripe price ID init
      config.py                # Pydantic settings from environment
      database.py              # Async engine, session factory, get_db dependency
      main.py                  # FastAPI app creation, router registration, startup events
    tests/
      conftest.py              # Fixtures: client, db, setup_db, register_and_login helper
      test_auth.py             # 10 auth endpoint tests
      test_content.py          # 13 content generation tests
      test_templates.py        # 17 template management tests
      test_images.py           # 12 image management tests
      test_billing.py          # 9 billing endpoint tests
      test_api_keys.py         # 5 API key tests
      test_health.py           # 1 health check test
    alembic/                   # Database migration scripts
    alembic.ini
    requirements.txt
  dashboard/
    src/
      service.config.ts        # Single source of truth: name, colors, fonts, nav, plans
      app/
        page.tsx               # Dashboard home (overview)
        login/page.tsx         # Login page
        register/page.tsx      # Registration page
        content/page.tsx       # Content generation page (Generate)
        templates/page.tsx     # Template management page
        billing/page.tsx       # Billing and subscription page
        api-keys/page.tsx      # API key management page
        settings/page.tsx      # User settings page
  master-landing/
    src/                       # Static landing page
  docs/
    DEVELOPER.md               # This file
    QA_ENGINEER.md
    PROJECT_MANAGER.md
    END_USER.md
    IMPLEMENTATION_STEPS.md
  README.md
```

---

## Database Migrations

ContentForge uses Alembic for schema migrations with the async SQLAlchemy engine.

```bash
# Create a new migration
cd backend && alembic revision --autogenerate -m "description of change"

# Run all pending migrations
cd backend && alembic upgrade head

# Rollback the last migration
cd backend && alembic downgrade -1

# View migration history
cd backend && alembic history

# Merge multiple migration heads (if parallel branches create conflicts)
cd backend && alembic merge heads -m "merge heads"
```

### Database Tables

| Table | Model | Purpose |
|-------|-------|---------|
| `users` | `User` | User accounts with email, hashed password, plan tier |
| `api_keys` | `ApiKey` | SHA-256 hashed API keys with scopes |
| `subscriptions` | `Subscription` | Stripe subscription state (synced via webhooks) |
| `generation_jobs` | `GenerationJob` | Content generation job tracking (pending/processing/completed/failed) |
| `generated_content` | `GeneratedContent` | Individual content items (title, description, meta, keywords, bullets) |
| `image_jobs` | `ImageJob` | Image download/optimization tracking |
| `templates` | `Template` | System and custom content generation templates |

---

## Testing

### Run All Tests

```bash
make test-backend    # 45 backend unit tests
```

### Run Specific Test Files

```bash
cd backend && pytest tests/test_content.py -v      # Content generation tests
cd backend && pytest tests/test_templates.py -v     # Template management tests
cd backend && pytest tests/test_images.py -v        # Image management tests
cd backend && pytest tests/test_auth.py -v          # Authentication tests
cd backend && pytest tests/test_billing.py -v       # Billing tests
cd backend && pytest tests/test_api_keys.py -v      # API key tests
cd backend && pytest tests/test_health.py -v        # Health check tests
```

### Test Architecture

- All tests use `pytest-asyncio` for async test support
- `httpx.AsyncClient` is used as the HTTP test client against the FastAPI app
- Database tables are **truncated between tests** via the `setup_db` autouse fixture
- The `register_and_login()` helper creates a user and returns auth headers
- Stripe runs in **mock mode** (no real API calls) when `STRIPE_SECRET_KEY` is empty
- AI content generation uses **mock content** (realistic text without calling Claude API)

### Test Fixtures (conftest.py)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `event_loop` | session | Single event loop for all tests |
| `setup_db` | function (autouse) | Creates tables, truncates after each test |
| `db` | function | Raw AsyncSession for direct DB operations |
| `client` | function | httpx AsyncClient for API testing |
| `auth_headers` | function | Pre-authenticated Bearer token headers |

---

## API Conventions

- **Base path**: All API routes are prefixed with `/api/v1/`
- **Authentication**: Bearer JWT token via `Authorization: Bearer <token>` header, or API key via `X-API-Key: <key>` header
- **Pagination**: `?page=1&per_page=20` query params; response includes `{ items, total, page, per_page }`
- **Errors**: Standard HTTP status codes with `{ "detail": "error message" }` JSON body
- **IDs**: All resource IDs are UUID v4
- **Timestamps**: ISO 8601 format (UTC)
- **Status codes**: 200 (success), 201 (created), 204 (deleted), 400 (bad request), 401 (unauthorized), 403 (forbidden/plan limit), 404 (not found), 409 (conflict), 422 (validation error)

---

## Design System

The dashboard uses a config-driven design defined in `dashboard/src/service.config.ts`.

| Property | Value |
|----------|-------|
| **Primary Color** | Violet Purple -- `oklch(0.60 0.22 300)` / `#8b5cf6` |
| **Accent Color** | Soft Lavender -- `oklch(0.75 0.18 280)` / `#a78bfa` |
| **Heading Font** | Clash Display (bold display font for creative/content branding) |
| **Body Font** | Satoshi (modern geometric sans for clean body text) |

### Navigation Items

The sidebar is driven by `serviceConfig.navigation`:

| Label | Route | Icon |
|-------|-------|------|
| Dashboard | `/` | LayoutDashboard |
| Generate | `/generate` | Sparkles |
| Templates | `/templates` | FileText |
| Images | `/images` | Image |
| History | `/history` | Clock |
| API Keys | `/api-keys` | Key |
| Billing | `/billing` | CreditCard |
| Settings | `/settings` | Settings |

---

## Key Design Decisions

1. **Independent user table per service**: Each service (ContentForge, etc.) maintains its own `users` table. Users can sign up directly or be provisioned via the dropshipping platform's `/auth/provision` endpoint. This allows services to run standalone or integrated.

2. **Plan limits enforced at API layer**: Plan quotas (generations/month, images/month) are checked in `content_service.py` before creating jobs. The `PLAN_LIMITS` dict in `constants/plans.py` is the single source of truth for tier limits.

3. **Mock mode for AI and Stripe**: When `ANTHROPIC_API_KEY` or `STRIPE_SECRET_KEY` are not set, the service operates in mock mode. Content generation produces realistic mock text via `generate_mock_content()`. Stripe checkout creates subscriptions directly in the database without calling Stripe. This enables full local development without external dependencies.

4. **Config-driven dashboard**: `service.config.ts` is the single source of truth for branding (name, colors, fonts), navigation, and plan tiers. Changing this file updates the entire dashboard appearance.

5. **API key authentication**: API keys are hashed with SHA-256 before storage. The raw key is only returned once at creation time. The `key_prefix` (first 12 characters) is stored for identification in the UI. The `get_current_user_or_api_key` dependency supports both JWT and API key auth.

6. **Cascading deletes**: Deleting a `GenerationJob` cascades to all `GeneratedContent` and `ImageJob` records via SQLAlchemy `cascade="all, delete-orphan"`. Deleting an `ImageJob` does NOT delete the parent job.

7. **Template system**: System templates (Professional, Casual, Luxury, SEO-Focused) are seeded at startup via `template_seeder.py` and are read-only. Users create custom templates with their preferred tone, style, and content types. Templates control AI prompt parameters.

8. **Pricing service**: The `pricing_service.py` module provides standalone markup calculation with psychological rounding strategies (round_99, round_95, round_00, none). It is a pure utility with no database dependencies.
