# Developer Guide

**For Developers:** TrendScout is an independently hostable SaaS product that discovers trending, high-potential products using multi-source data aggregation and AI-powered scoring. It follows the standard service template (FastAPI + SQLAlchemy 2.0 async + Celery) and can run standalone or as an integrated add-on to the dropshipping platform. Feature logic lives in `backend/app/services/research_service.py`, `backend/app/services/scoring_service.py`, and `backend/app/services/ai_analysis_service.py`. The dashboard is config-driven via `dashboard/src/service.config.ts`.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend API | FastAPI | Latest |
| ORM | SQLAlchemy 2.0 (async) | 2.x |
| Database | PostgreSQL | 16 |
| Cache / Queue | Redis | 7 |
| Task Queue | Celery | 5.x |
| Migrations | Alembic | Latest |
| Dashboard | Next.js (App Router) | 16 |
| Styling | Tailwind CSS | 4.x |
| Landing Page | Next.js (static export) | 16 |
| Auth | JWT (python-jose) + bcrypt | -- |
| AI Analysis | Anthropic Claude API | claude-sonnet-4-20250514 |
| Billing | Stripe (mock mode supported) | -- |
| Testing | pytest + pytest-asyncio + httpx | -- |

---

## Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16
- Redis 7

### Install Dependencies

```bash
# Backend
cd services/trendscout/backend
pip install -r requirements.txt

# Dashboard
cd services/trendscout/dashboard
npm install

# Landing page
cd services/trendscout/landing
npm install
```

### Start Services

```bash
# Start all services (from service root)
make install
make migrate
make start
```

Or start each service individually:

```bash
# Backend API (port 8101)
cd services/trendscout/backend
uvicorn app.main:app --host 0.0.0.0 --port 8101 --reload

# Celery worker
cd services/trendscout/backend
celery -A app.tasks.celery_app worker -l info -Q trendscout

# Dashboard (port 3101)
cd services/trendscout/dashboard
npm run dev -- -p 3101

# Landing page (port 3201)
cd services/trendscout/landing
npm run dev -- -p 3201
```

### Docker

```bash
docker-compose up
```

---

## Services

| Service | Command | Port |
|---------|---------|------|
| Backend API | `uvicorn app.main:app --port 8101` | 8101 |
| Dashboard | `npm run dev -- -p 3101` | 3101 |
| Landing Page | `npm run dev -- -p 3201` | 3201 |
| PostgreSQL | Docker / system service | 5501 |
| Redis | Docker / system service | 6401 |
| Celery Worker | `celery -A app.tasks.celery_app worker -Q trendscout` | -- |

### Ports Table

| Port | Service | Description |
|------|---------|-------------|
| 8101 | Backend API | FastAPI server, Swagger at `/docs`, ReDoc at `/redoc` |
| 3101 | Dashboard | Next.js App Router dashboard for users |
| 3201 | Landing Page | Next.js static marketing/landing site |
| 5501 | PostgreSQL | Database server |
| 6401 | Redis | Cache, Celery broker, and result backend |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | `trendscout` | Internal service identifier |
| `SERVICE_DISPLAY_NAME` | `TrendScout` | Human-readable product name |
| `SERVICE_PORT` | `8101` | Backend listening port |
| `DEBUG` | `false` | Enable debug mode with SQL logging |
| `DATABASE_URL` | `postgresql+asyncpg://trendscout:trendscout_dev@localhost:5432/trendscout` | Async PostgreSQL connection |
| `DATABASE_URL_SYNC` | `postgresql://trendscout:trendscout_dev@localhost:5432/trendscout` | Sync connection (Alembic, Celery) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis cache URL |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery task broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery result store |
| `JWT_SECRET_KEY` | `dev-secret-change-in-production` | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `CORS_ORIGINS` | `http://localhost:3101` | Comma-separated allowed origins |
| `STRIPE_SECRET_KEY` | (empty = mock mode) | Stripe API secret |
| `STRIPE_WEBHOOK_SECRET` | (empty) | Stripe webhook signing secret |
| `STRIPE_PRO_PRICE_ID` | (empty) | Stripe Price ID for Pro tier |
| `STRIPE_ENTERPRISE_PRICE_ID` | (empty) | Stripe Price ID for Enterprise tier |
| `STRIPE_BILLING_SUCCESS_URL` | `http://localhost:3101/billing?success=true` | Post-checkout redirect |
| `STRIPE_BILLING_CANCEL_URL` | `http://localhost:3101/billing?canceled=true` | Checkout cancel redirect |
| `ANTHROPIC_API_KEY` | (empty = mock analysis) | Anthropic API key for Claude |

---

## Project Structure

```
services/trendscout/
├── backend/
│   ├── app/
│   │   ├── api/                    # API route modules
│   │   │   ├── auth.py             # Register, login, refresh, profile, provision
│   │   │   ├── billing.py          # Plans, checkout, portal, overview
│   │   │   ├── research.py         # Research run CRUD, result detail
│   │   │   ├── watchlist.py        # Watchlist add/list/update/delete
│   │   │   ├── sources.py          # Source config CRUD
│   │   │   ├── api_keys.py         # API key create/list/revoke
│   │   │   └── deps.py             # Auth dependencies (JWT, API key)
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── base.py             # DeclarativeBase
│   │   │   ├── user.py             # User + PlanTier enum
│   │   │   ├── subscription.py     # Stripe subscription state
│   │   │   ├── api_key.py          # API key (SHA-256 hashed)
│   │   │   ├── research.py         # ResearchRun + ResearchResult
│   │   │   ├── watchlist.py        # WatchlistItem
│   │   │   ├── source_config.py    # SourceConfig
│   │   │   └── __init__.py         # Model exports for Alembic
│   │   ├── services/               # Business logic layer
│   │   │   ├── auth_service.py     # Registration, login, JWT, provisioning
│   │   │   ├── billing_service.py  # Stripe checkout/portal/webhooks
│   │   │   ├── research_service.py # Run/result/watchlist/source CRUD + limits
│   │   │   ├── scoring_service.py  # Weighted composite scoring (5 dimensions)
│   │   │   └── ai_analysis_service.py # Claude AI analysis (+ mock fallback)
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── auth.py             # Auth request/response schemas
│   │   │   ├── billing.py          # Billing schemas
│   │   │   └── research.py         # Research, watchlist, source schemas
│   │   ├── tasks/                  # Celery background tasks
│   │   │   ├── celery_app.py       # Celery app configuration
│   │   │   └── research_tasks.py   # run_research task + mock data generators
│   │   ├── constants/
│   │   │   └── plans.py            # PlanLimits dataclass + PLAN_LIMITS dict
│   │   ├── utils/
│   │   │   └── helpers.py          # Billing period calculator
│   │   ├── config.py               # Pydantic Settings (env vars)
│   │   ├── database.py             # Async engine + session factory
│   │   └── main.py                 # FastAPI app creation + route mounting
│   ├── alembic/                    # Database migrations
│   ├── tests/                      # Backend test suite
│   │   ├── conftest.py             # Fixtures: client, db, auth_headers
│   │   ├── test_auth.py            # Auth endpoint tests (10 tests)
│   │   ├── test_billing.py         # Billing endpoint tests (9 tests)
│   │   ├── test_research.py        # Research CRUD tests (21 tests)
│   │   ├── test_watchlist.py       # Watchlist CRUD tests (24 tests)
│   │   ├── test_sources.py         # Source config tests (22 tests)
│   │   ├── test_api_keys.py        # API key tests (5 tests)
│   │   └── test_health.py          # Health check test (1 test)
│   └── requirements.txt
├── dashboard/
│   └── src/
│       ├── app/
│       │   ├── page.tsx            # Dashboard home (overview)
│       │   ├── login/page.tsx      # Login page
│       │   ├── register/page.tsx   # Registration page
│       │   ├── research/page.tsx   # Research runs page
│       │   ├── watchlist/page.tsx  # Watchlist management page
│       │   ├── billing/page.tsx    # Billing & subscription page
│       │   ├── api-keys/page.tsx   # API key management page
│       │   └── settings/page.tsx   # User settings page
│       └── service.config.ts       # Service branding, nav, plans
├── landing/
│   └── src/
│       └── app/
│           ├── page.tsx            # Landing page (hero, features, CTA)
│           └── pricing/page.tsx    # Pricing page
├── docs/                           # Documentation (this directory)
└── README.md                       # Service overview
```

---

## Database Migrations

```bash
# Generate a new migration after model changes
cd services/trendscout/backend
alembic revision --autogenerate -m "description of changes"

# Apply all pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history

# Handle multiple heads (parallel migration branches)
alembic merge heads -m "merge heads"
alembic upgrade head
```

### Database Tables

| Table | Model | Purpose |
|-------|-------|---------|
| `users` | `User` | User accounts (email, password, plan, Stripe, external IDs) |
| `subscriptions` | `Subscription` | Stripe subscription state (status, period, plan) |
| `api_keys` | `ApiKey` | API keys for programmatic access (SHA-256 hashed) |
| `research_runs` | `ResearchRun` | Research job tracking (keywords, sources, status, score_config) |
| `research_results` | `ResearchResult` | Individual product results with scores and AI analysis |
| `watchlist_items` | `WatchlistItem` | Saved results for review/import (unique per user+result) |
| `source_configs` | `SourceConfig` | Per-user data source credentials and settings |

---

## Testing

```bash
# Run all backend tests
cd services/trendscout/backend
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_research.py

# Run a specific test
pytest tests/test_research.py::test_create_research_run -v

# Run with coverage
pytest --cov=app tests/
```

**Test count:** 67 backend tests across 7 test files (auth, billing, research, watchlist, sources, API keys, health).

All tests run in **mock Stripe mode** (no real Stripe API calls) and use the same database with table truncation between tests for isolation.

---

## API Conventions

### Base URL

All endpoints are prefixed with `/api/v1/`.

### Authentication

Two auth methods are supported:

1. **Bearer JWT Token** (dashboard users):
   ```
   Authorization: Bearer <access_token>
   ```

2. **API Key** (programmatic access):
   ```
   X-API-Key: <api_key>
   ```

### Pagination

Paginated list endpoints follow a standard response format:

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

Query parameters: `?page=1&per_page=20`

### Error Responses

```json
{
  "detail": "Human-readable error message"
}
```

Standard HTTP status codes:
- `200` Success
- `201` Created
- `204` No Content (delete operations)
- `400` Bad Request (validation errors)
- `401` Unauthorized (missing/invalid auth)
- `403` Forbidden (plan limit exceeded)
- `404` Not Found (resource missing or not owned)
- `409` Conflict (duplicate resource)
- `422` Unprocessable Entity (schema validation)

---

## Design System

| Element | Value |
|---------|-------|
| Primary Color | Electric Blue -- `oklch(0.65 0.20 250)` / `#3b82f6` |
| Accent Color | Cyan -- `oklch(0.75 0.15 200)` / `#38bdf8` |
| Heading Font | Space Grotesk (geometric sans-serif, tech/data feel) |
| Body Font | Inter (highly legible, UI-optimized) |

The design system is configured in `dashboard/src/service.config.ts` and applied globally via CSS variables and the Next.js layout.

---

## Key Design Decisions

1. **Independent SaaS Architecture**: TrendScout is a standalone product with its own database, auth, and billing. It shares no code or database with the dropshipping platform. Integration happens via HTTP API (provision endpoint + API keys).

2. **No Shared Code Imports**: The service template enforces zero imports from the platform backend. Each service is fully self-contained and independently deployable.

3. **Config-Driven Dashboard**: All branding, navigation, colors, fonts, and plan definitions are controlled by `service.config.ts`. Creating a new service from the template only requires replacing configuration values.

4. **Plan Enforcement at Service Layer**: Resource limits (research runs/month, watchlist items) are enforced in `research_service.py`, not in the API routes. This keeps routes thin and business logic centralized.

5. **Mock Mode for Local Development**: Both Stripe billing and AI analysis support mock mode (empty API keys). Tests and local development work without external service dependencies. Mock data generators in `research_tasks.py` produce realistic, deterministic product data.

6. **Credential Redaction**: Source config credentials are never returned in API responses. Only a `has_credentials` boolean flag indicates whether credentials have been configured.

7. **Scoring Algorithm**: Products are scored across 5 weighted dimensions (Social 40%, Market 30%, Competition 15%, SEO 10%, Fundamentals 5%). Users can override weights via `score_config` on individual research runs.

8. **Celery for Background Processing**: Research runs are dispatched to Celery tasks for asynchronous execution. The API returns immediately with a `pending` status, and clients poll for completion.
