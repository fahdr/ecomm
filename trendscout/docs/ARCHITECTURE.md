# TrendScout Architecture

> Part of [TrendScout](README.md) documentation

This document describes the technical architecture, project structure, database schema, and key design decisions for the TrendScout service.

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

## Project Structure

```
trendscout/
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

## Database Schema

### Tables

| Table | Model | Purpose |
|-------|-------|---------|
| `users` | `User` | User accounts (email, password, plan, Stripe, external IDs) |
| `subscriptions` | `Subscription` | Stripe subscription state (status, period, plan) |
| `api_keys` | `ApiKey` | API keys for programmatic access (SHA-256 hashed) |
| `research_runs` | `ResearchRun` | Research job tracking (keywords, sources, status, score_config) |
| `research_results` | `ResearchResult` | Individual product results with scores and AI analysis |
| `watchlist_items` | `WatchlistItem` | Saved results for review/import (unique per user+result) |
| `source_configs` | `SourceConfig` | Per-user data source credentials and settings |

### Key Relationships

- `User` → `Subscription` (one-to-one, optional)
- `User` → `ApiKey[]` (one-to-many)
- `User` → `ResearchRun[]` (one-to-many)
- `User` → `WatchlistItem[]` (one-to-many)
- `User` → `SourceConfig[]` (one-to-many)
- `ResearchRun` → `ResearchResult[]` (one-to-many, cascade delete)
- `ResearchResult` → `WatchlistItem[]` (one-to-many, cascade delete)

---

## Key Design Decisions

### 1. Independent SaaS Architecture

TrendScout is a standalone product with its own database, auth, and billing. It shares no code or database with the dropshipping platform. Integration happens via HTTP API (provision endpoint + API keys).

### 2. No Shared Code Imports

The service template enforces zero imports from the platform backend. Each service is fully self-contained and independently deployable.

### 3. Config-Driven Dashboard

All branding, navigation, colors, fonts, and plan definitions are controlled by `service.config.ts`. Creating a new service from the template only requires replacing configuration values.

### 4. Plan Enforcement at Service Layer

Resource limits (research runs/month, watchlist items) are enforced in `research_service.py`, not in the API routes. This keeps routes thin and business logic centralized.

### 5. Mock Mode for Local Development

Both Stripe billing and AI analysis support mock mode (empty API keys). Tests and local development work without external service dependencies. Mock data generators in `research_tasks.py` produce realistic, deterministic product data.

### 6. Credential Redaction

Source config credentials are never returned in API responses. Only a `has_credentials` boolean flag indicates whether credentials have been configured.

### 7. Scoring Algorithm

Products are scored across 5 weighted dimensions:
- **Social** (40%): Engagement metrics, viral reach, trending status
- **Market** (30%): Search volume, order counts, growth rate
- **Competition** (15%): Seller count, market saturation, review quality
- **SEO** (10%): Keyword relevance, search position, content quality
- **Fundamentals** (5%): Price range, margin potential, shipping time

Users can override weights via `score_config` on individual research runs.

### 8. Celery for Background Processing

Research runs are dispatched to Celery tasks for asynchronous execution. The API returns immediately with a `pending` status, and clients poll for completion.

### 9. Schema-Based Test Isolation

All tests run in a dedicated PostgreSQL schema (`trendscout_test`) to avoid conflicts with other services sharing the same database. Each test truncates all tables with CASCADE for isolation.

---

## Platform Event Webhook

Each service receives platform events from the dropshipping backend via `POST /api/v1/webhooks/platform-events`. Events are HMAC-SHA256 signed using `platform_webhook_secret`. The receiver verifies the signature and routes events to service-specific handlers.

This allows the dropshipping platform to notify TrendScout of relevant events (e.g., user plan changes, account suspensions) without direct database access.

---

## Design System

| Element | Value |
|---------|-------|
| Primary Color | Electric Blue -- `oklch(0.65 0.20 250)` / `#3b82f6` |
| Accent Color | Cyan -- `oklch(0.75 0.15 200)` / `#38bdf8` |
| Heading Font | Syne (expressive geometric sans-serif, bold tech personality) |
| Body Font | DM Sans (clean, modern, highly readable) |

The design system is configured in `dashboard/src/service.config.ts` and applied globally via CSS variables and the Next.js layout.

---

## Scoring Service Architecture

The `scoring_service.py` module calculates composite product scores using a weighted multi-dimensional algorithm:

```python
# Default weights
DEFAULT_WEIGHTS = {
    "social": 0.40,      # Engagement, virality, trending status
    "market": 0.30,      # Search volume, orders, growth
    "competition": 0.15, # Seller density, saturation
    "seo": 0.10,        # Keyword relevance, position
    "fundamentals": 0.05 # Price, margin, logistics
}
```

Each dimension is scored 0-100 using sub-metrics from the raw product data. The final score is a weighted average, clamped to [0, 100] and rounded to 1 decimal place.

---

## AI Analysis Service Architecture

The `ai_analysis_service.py` module provides product analysis via Anthropic Claude:

- **Real Mode**: Calls Claude API with structured prompt requesting JSON output
- **Mock Mode**: Generates deterministic analysis using MD5 hash of product title
- **Graceful Fallback**: Missing API key or API errors automatically fall back to mock

Analysis output includes:
- Summary (concise assessment)
- Opportunity score (0-100)
- Risk factors (3 specific concerns)
- Recommended price range
- Target audience description
- Marketing angles (3 strategies)

---

*See also: [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
