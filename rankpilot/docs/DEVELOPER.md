# RankPilot Developer Guide

## Introduction

RankPilot is an independently hostable SaaS product that automates search engine optimization for e-commerce stores. It manages sitemaps, JSON-LD schema markup, AI-generated blog posts, keyword rank tracking, and comprehensive SEO audits. RankPilot can be used as a standalone product or integrated with the dropshipping platform via cross-service provisioning and API key authentication.

RankPilot is **Feature A3** in the overall platform roadmap and has the most API endpoints of any service in the ecosystem (5 domain-specific route files, 20+ endpoints total).

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend API | FastAPI + SQLAlchemy 2.0 (async) | Python 3.12 |
| Database | PostgreSQL | 16 |
| Cache / Message Queue | Redis | 7 |
| Task Queue | Celery | latest |
| Dashboard | Next.js (App Router) + Tailwind CSS | Next.js 16 |
| Landing Page | Next.js (static export) | Next.js 16 |
| ORM Migrations | Alembic | latest |
| Password Hashing | bcrypt | latest |
| JWT Auth | python-jose / PyJWT | latest |
| HTTP Test Client | httpx + pytest-asyncio | latest |

---

## Local Development

### Ports

| Service | Port | Purpose |
|---------|------|---------|
| Backend API | **8103** | FastAPI application + Swagger docs at `/docs` |
| Dashboard | **3103** | Next.js 16 dashboard (App Router) |
| Landing Page | **3203** | Next.js 16 static marketing site |
| PostgreSQL | **5503** | Database |
| Redis | **6403** | Cache and Celery broker |

### Quick Start

```bash
# Install dependencies, run migrations, and start all services
make install && make migrate && make start
```

### Access Points

- **API**: http://localhost:8103
- **API Docs (Swagger)**: http://localhost:8103/docs
- **Dashboard**: http://localhost:3103
- **Landing Page**: http://localhost:3203

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://dropship:dropship_dev@db:5503/rankpilot` |
| `DATABASE_URL_SYNC` | PostgreSQL sync connection string (Alembic) | `postgresql://dropship:dropship_dev@db:5503/rankpilot` |
| `REDIS_URL` | Redis connection for caching | `redis://redis:6403/0` |
| `CELERY_BROKER_URL` | Redis connection for Celery broker | `redis://redis:6403/1` |
| `CELERY_RESULT_BACKEND` | Redis connection for Celery results | `redis://redis:6403/2` |
| `JWT_SECRET_KEY` | Secret key for JWT token signing | (required) |
| `STRIPE_SECRET_KEY` | Stripe API key (empty = mock mode) | `""` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signature secret | `""` |
| `STRIPE_PRO_PRICE_ID` | Stripe Price ID for Pro tier | `""` |
| `STRIPE_ENTERPRISE_PRICE_ID` | Stripe Price ID for Enterprise tier | `""` |
| `NEXT_PUBLIC_API_URL` | Dashboard -> Backend API URL | `http://localhost:8103` |

---

## Project Structure

```
services/rankpilot/
|-- README.md                          # Service overview and API reference
|-- Makefile                           # Build, test, and run targets
|-- docker-compose.yml                 # Local dev orchestration
|-- docs/                              # Documentation (this directory)
|   |-- DEVELOPER.md                   # This file
|   |-- QA_ENGINEER.md                 # QA testing guide
|   |-- PROJECT_MANAGER.md            # PM overview
|   |-- END_USER.md                    # End user guide
|   |-- IMPLEMENTATION_STEPS.md        # Build history
|
|-- backend/
|   |-- Dockerfile                     # Backend container
|   |-- alembic/                       # Database migrations
|   |   |-- env.py                     # Alembic config
|   |   |-- versions/                  # Migration scripts
|   |-- app/
|   |   |-- main.py                    # FastAPI app entry point
|   |   |-- config.py                  # Settings (env vars)
|   |   |-- database.py                # Async engine + session factory
|   |   |-- api/                       # Route handlers (13 files)
|   |   |   |-- __init__.py
|   |   |   |-- auth.py               # Register, login, refresh, profile, provision
|   |   |   |-- deps.py               # Dependency injection (JWT + API key auth)
|   |   |   |-- health.py             # GET /health
|   |   |   |-- sites.py              # Site CRUD + domain verification
|   |   |   |-- blog_posts.py         # Blog post CRUD + AI generation
|   |   |   |-- keywords.py           # Keyword tracking CRUD + rank refresh
|   |   |   |-- audits.py             # Run audit + list/get audit history
|   |   |   |-- schema.py             # JSON-LD schema CRUD + preview
|   |   |   |-- billing.py            # Plans, checkout, portal, overview
|   |   |   |-- api_keys.py           # API key create, list, revoke
|   |   |   |-- usage.py              # Usage reporting endpoint
|   |   |   |-- webhooks.py           # Stripe webhook handler
|   |   |-- models/                    # SQLAlchemy models (10 files)
|   |   |   |-- base.py               # DeclarativeBase
|   |   |   |-- user.py               # User + PlanTier enum
|   |   |   |-- subscription.py       # Stripe subscription
|   |   |   |-- api_key.py            # API key (hashed)
|   |   |   |-- site.py               # Site (domain for SEO tracking)
|   |   |   |-- blog_post.py          # Blog post (AI-generated content)
|   |   |   |-- keyword.py            # Keyword tracking record
|   |   |   |-- seo_audit.py          # SEO audit result
|   |   |   |-- schema_config.py      # JSON-LD schema config
|   |   |   |-- __init__.py           # Exports all models for Alembic
|   |   |-- schemas/                   # Pydantic schemas
|   |   |   |-- auth.py               # Auth request/response schemas
|   |   |   |-- billing.py            # Billing schemas
|   |   |   |-- seo.py                # SEO domain schemas (sites, posts, keywords, audits, schema)
|   |   |-- services/                  # Business logic layer (8 files)
|   |   |   |-- auth_service.py        # Registration, login, JWT, API key auth
|   |   |   |-- billing_service.py     # Stripe checkout, portal, usage
|   |   |   |-- site_service.py        # Site CRUD + verification
|   |   |   |-- blog_service.py        # Blog post CRUD + AI content generation (mock)
|   |   |   |-- keyword_service.py     # Keyword CRUD + rank update (mock)
|   |   |   |-- audit_service.py       # Audit execution + scoring (mock)
|   |   |   |-- schema_service.py      # JSON-LD generation + preview rendering
|   |   |-- constants/
|   |   |   |-- plans.py               # Plan tier limits (PlanLimits dataclass)
|   |   |-- tasks/
|   |   |   |-- celery_app.py          # Celery configuration
|   |   |-- utils/
|   |       |-- helpers.py             # Utility functions
|   |-- tests/                         # Backend tests (8 test files)
|       |-- conftest.py                # Fixtures (client, db, auth_headers)
|       |-- test_auth.py               # 11 auth tests
|       |-- test_health.py             # 1 health test
|       |-- test_sites.py              # 20 site tests
|       |-- test_blog.py               # 25 blog post tests
|       |-- test_keywords.py           # 16 keyword tests
|       |-- test_audits.py             # 15 audit tests
|       |-- test_billing.py            # 10 billing tests
|       |-- test_api_keys.py           # 5 API key tests
|
|-- dashboard/
|   |-- package.json
|   |-- tsconfig.json
|   |-- next.config.ts
|   |-- src/
|       |-- service.config.ts          # Branding, navigation, plans (single source of truth)
|       |-- lib/
|       |   |-- api.ts                 # HTTP client for backend
|       |   |-- auth.ts                # JWT token management
|       |   |-- utils.ts               # Utility functions
|       |-- app/
|       |   |-- layout.tsx             # Root layout with fonts + shell
|       |   |-- page.tsx               # Dashboard home
|       |   |-- login/page.tsx         # Login page
|       |   |-- register/page.tsx      # Registration page
|       |   |-- sites/page.tsx         # Site management
|       |   |-- keywords/page.tsx      # Keyword tracking
|       |   |-- audits/page.tsx        # SEO audit history
|       |   |-- billing/page.tsx       # Subscription management
|       |   |-- api-keys/page.tsx      # API key management
|       |   |-- settings/page.tsx      # Account settings
|       |-- components/
|           |-- shell.tsx              # Layout shell wrapper
|           |-- sidebar.tsx            # Sidebar navigation
|           |-- top-bar.tsx            # Top bar
|           |-- motion.tsx             # Animation primitives
|           |-- ui/                    # Reusable UI components (badge, button, card, dialog, input, skeleton)
|
|-- landing/                           # Static marketing site (Next.js)
    |-- src/app/page.tsx               # Landing page
```

---

## Testing

### Running Tests

```bash
# Run all 74 backend tests
make test-backend

# Run with verbose output
pytest backend/tests -v

# Run a specific test file
pytest backend/tests/test_sites.py -v

# Run a specific test
pytest backend/tests/test_blog.py::test_create_blog_post_basic -v
```

### Test Distribution

| Test File | Count | Coverage Area |
|-----------|-------|--------------|
| `test_auth.py` | 11 | Registration, login, refresh, profile, duplicate email |
| `test_health.py` | 1 | Health check endpoint |
| `test_sites.py` | 20 | Site CRUD, pagination, verification, cross-user isolation |
| `test_blog.py` | 25 | Blog post CRUD, AI generation, plan limits, status transitions |
| `test_keywords.py` | 16 | Keyword CRUD, duplicates, rank refresh, cross-user isolation |
| `test_audits.py` | 15 | Audit execution, history, pagination, cross-user isolation |
| `test_billing.py` | 10 | Plan listing, checkout, overview, subscription lifecycle |
| `test_api_keys.py` | 5 | Key creation, listing, revocation, API key auth |
| **Total** | **74** | |

### Test Fixtures (conftest.py)

- **`setup_db`** (autouse): Creates tables before tests, truncates all tables with CASCADE after each test. Terminates non-self DB connections to prevent deadlocks.
- **`client`**: Provides an `httpx.AsyncClient` configured for the FastAPI app.
- **`db`**: Provides a raw `AsyncSession` for direct DB access in tests.
- **`auth_headers`**: Registers a test user and returns `{"Authorization": "Bearer <token>"}`.
- **`register_and_login(client, email)`**: Helper to register a user and return auth headers.

---

## API Conventions

### Authentication

All protected endpoints require either:
1. **Bearer JWT**: `Authorization: Bearer <access_token>` -- from `/auth/register` or `/auth/login`
2. **API Key**: `X-API-Key: <raw_key>` -- from `POST /api-keys` (only for certain endpoints like `/usage`)

The `get_current_user` dependency extracts the user from a JWT. The `get_current_user_or_api_key` dependency accepts either method.

### Pagination

All list endpoints return paginated responses:

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### Error Responses

| Code | Meaning |
|------|---------|
| 400 | Bad request (validation, duplicate resource) |
| 401 | Not authenticated (missing/invalid token) |
| 403 | Plan limit reached (upgrade required) |
| 404 | Resource not found (or not owned by user) |
| 409 | Conflict (duplicate email on registration) |
| 422 | Validation error (Pydantic schema failure) |

### Plan Limits

Plan limits are enforced at the API layer via the `PLAN_LIMITS` dict in `constants/plans.py`:

| Tier | Blog Posts/Month (`max_items`) | Keywords (`max_secondary`) | Sites | API Access | Trial Days |
|------|------|------|------|------|------|
| Free | 2 | 20 | 1 | No | 0 |
| Pro | 20 | 200 | 5 | Yes | 14 |
| Enterprise | -1 (unlimited) | -1 (unlimited) | Unlimited | Yes | 14 |

### Sentinel Value Pattern

Update functions use Python's `Ellipsis` (`...`) as a sentinel to distinguish "field not provided" from "set field to None":

```python
async def update_site(
    db, site,
    domain=None,
    sitemap_url=...,  # Ellipsis = not provided, None = clear the value
    status=None,
):
    if sitemap_url is not ...:
        site.sitemap_url = sitemap_url
```

---

## Design System

The dashboard uses a config-driven design system defined in `dashboard/src/service.config.ts`:

- **Primary Color**: Emerald Green -- `oklch(0.65 0.18 155)` / `#10b981`
- **Accent Color**: Light Green -- `oklch(0.72 0.15 140)` / `#34d399`
- **Heading Font**: General Sans (clean, trustworthy)
- **Body Font**: Inter

### Dashboard Navigation

The sidebar is driven by the `navigation` array in `service.config.ts`:

| Label | Route | Icon |
|-------|-------|------|
| Dashboard | `/` | LayoutDashboard |
| Sites | `/sites` | Globe |
| Blog Posts | `/blog-posts` | FileText |
| Keywords | `/keywords` | Search |
| Audits | `/audits` | ClipboardCheck |
| Schema | `/schema` | Code |
| API Keys | `/api-keys` | Key |
| Billing | `/billing` | CreditCard |
| Settings | `/settings` | Settings |

---

## Key Architectural Decisions

1. **Independent User Table**: RankPilot maintains its own `users` table. Users can register directly or be provisioned via the platform's `/auth/provision` endpoint.
2. **Denormalized Plan Field**: The `User.plan` field is a denormalized copy of the subscription tier for fast lookups. It is updated whenever the subscription changes (via webhook or mock checkout).
3. **Cross-Service Integration**: The `/auth/provision` and `/usage` endpoints enable the dropshipping platform to create users and poll usage data via API key authentication.
4. **Mock Implementations**: AI blog generation, keyword rank checking, SEO audits, and domain verification all use mock implementations. Production versions would call external APIs (Anthropic, SerpAPI, site crawlers).
5. **Cascade Deletes**: Deleting a site cascades to all blog posts, keywords, audits, and schema configs. Deleting a user cascades to all sites.
6. **Config-Driven Dashboard**: The entire dashboard branding, navigation, and billing UI is driven by `service.config.ts`. Changing this single file updates the entire frontend.

---

## Database Tables

| Table | Primary Model | Key Columns |
|-------|--------------|-------------|
| `users` | `User` | id, email, hashed_password, plan (PlanTier enum), stripe_customer_id, external_platform_id |
| `subscriptions` | `Subscription` | id, user_id, plan, status, stripe_subscription_id |
| `api_keys` | `ApiKey` | id, user_id, key_hash (SHA-256), key_prefix, scopes, is_active |
| `sites` | `Site` | id, user_id, domain, sitemap_url, is_verified, verification_method, status, last_crawled |
| `blog_posts` | `BlogPost` | id, site_id, user_id, title, slug, content (TEXT), meta_description, keywords (ARRAY), status, word_count, published_at |
| `keyword_tracking` | `KeywordTracking` | id, site_id, keyword, current_rank, previous_rank, search_volume, difficulty, tracked_since, last_checked |
| `seo_audits` | `SeoAudit` | id, site_id, overall_score (0-100), issues (JSON), recommendations (JSON), pages_crawled |
| `schema_configs` | `SchemaConfig` | id, site_id, page_type, schema_json (JSON), is_active |

---

## Common Development Tasks

### Adding a New API Endpoint

1. Create or edit a route file in `backend/app/api/`.
2. Add the business logic function in `backend/app/services/`.
3. Add Pydantic schemas in `backend/app/schemas/` if needed.
4. Register the router in `backend/app/main.py` if it is a new file.
5. Write tests in `backend/tests/`.

### Adding a New Model

1. Create the model file in `backend/app/models/`.
2. Import it in `backend/app/models/__init__.py` (required for Alembic detection).
3. Run `alembic revision --autogenerate -m "add table_name"`.
4. Run `alembic upgrade head`.

### Adding a Dashboard Page

1. Create `dashboard/src/app/<route>/page.tsx`.
2. Add a navigation entry in `dashboard/src/service.config.ts`.
3. The sidebar picks up the new route automatically.
