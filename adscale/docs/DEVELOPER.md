# Developer Guide

**For Developers:** AdScale is the AI Ad Campaign Manager service (Feature A7) that provides dual-platform advertising management across Google Ads and Meta (Facebook + Instagram) Ads. It features AI-powered ad copy generation via Claude, automated campaign optimization with ROAS-based rules, budget management (daily and lifetime), performance metrics tracking (ROAS, CPA, CTR), and cascading resource relationships (ad accounts -> campaigns -> ad groups -> creatives). The service is independently deployable and can operate standalone or integrated with the dropshipping platform.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend API | FastAPI | Latest |
| ORM | SQLAlchemy 2.0 (async) | 2.x |
| Database | PostgreSQL | 16 |
| Cache / Queue Broker | Redis | 7 |
| Task Queue | Celery | Latest |
| Dashboard | Next.js (App Router) | 16 |
| Dashboard Styling | Tailwind CSS | Latest |
| Landing Page | Next.js (static) | 16 |
| Migrations | Alembic | Latest |
| Auth | JWT (access + refresh tokens) + API Key (SHA-256 hashed) |
| Testing | pytest + pytest-asyncio + httpx | Latest |

---

## Local Development

### Ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8107 | http://localhost:8107 |
| API Docs (Swagger) | 8107 | http://localhost:8107/docs |
| Dashboard | 3107 | http://localhost:3107 |
| Landing Page | 3207 | http://localhost:3207 |
| PostgreSQL | 5507 | `postgresql://dropship:dropship_dev@db:5507/dropshipping` |
| Redis | 6407 | `redis://localhost:6407/0` |

### Quick Start

```bash
make install && make migrate && make start
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://dropship:dropship_dev@db:5507/dropshipping` |
| `DATABASE_URL_SYNC` | Sync PostgreSQL connection (Alembic) | `postgresql://dropship:dropship_dev@db:5507/dropshipping` |
| `REDIS_URL` | Redis connection for cache | `redis://redis:6407/0` |
| `CELERY_BROKER_URL` | Celery broker (Redis) | `redis://redis:6407/1` |
| `CELERY_RESULT_BACKEND` | Celery result backend (Redis) | `redis://redis:6407/2` |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens | (required) |
| `STRIPE_SECRET_KEY` | Stripe API key for billing | (optional, mock mode if empty) |
| `STRIPE_PRO_PRICE_ID` | Stripe Price ID for Pro tier | (optional) |
| `STRIPE_ENTERPRISE_PRICE_ID` | Stripe Price ID for Enterprise tier | (optional) |
| `NEXT_PUBLIC_API_URL` | Dashboard -> Backend URL | `http://localhost:8107` |

---

## Project Structure

```
adscale/
├── README.md
├── Makefile
├── docker-compose.yml
├── docs/                           # Documentation (you are here)
│   ├── DEVELOPER.md
│   ├── QA_ENGINEER.md
│   ├── PROJECT_MANAGER.md
│   ├── END_USER.md
│   └── IMPLEMENTATION_STEPS.md
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Settings (env vars, service name)
│   │   ├── database.py             # Async SQLAlchemy engine + session
│   │   ├── api/                    # API route modules
│   │   │   ├── __init__.py         # Router aggregation
│   │   │   ├── deps.py             # Dependency injection (auth, plan limits)
│   │   │   ├── auth.py             # Register, login, refresh, profile, provision
│   │   │   ├── accounts.py         # Ad account connect/list/disconnect
│   │   │   ├── campaigns.py        # Campaign CRUD with plan limits
│   │   │   ├── ad_groups.py        # Ad group CRUD with plan limits
│   │   │   ├── creatives.py        # Creative CRUD + AI copy generation
│   │   │   ├── metrics.py          # Overview, per-campaign, date-range metrics
│   │   │   ├── rules.py            # Optimization rule CRUD + execute-now
│   │   │   ├── billing.py          # Plans, checkout, portal, subscription
│   │   │   ├── api_keys.py         # API key create/list/revoke
│   │   │   ├── usage.py            # Cross-service usage reporting
│   │   │   ├── health.py           # Health check endpoint
│   │   │   └── webhooks.py         # Stripe webhook handler
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py         # Model exports for Alembic
│   │   │   ├── base.py             # Declarative base
│   │   │   ├── user.py             # User + PlanTier enum
│   │   │   ├── subscription.py     # Stripe subscription tracking
│   │   │   ├── api_key.py          # SHA-256 hashed API keys
│   │   │   ├── ad_account.py       # AdAccount (Google/Meta) + enums
│   │   │   ├── campaign.py         # Campaign + objective/status enums
│   │   │   ├── ad_group.py         # AdGroup + bid strategy/status enums
│   │   │   ├── ad_creative.py      # AdCreative + approval status enum
│   │   │   ├── campaign_metrics.py # Daily metrics (impressions, clicks, ROAS...)
│   │   │   └── optimization_rule.py# Rule + RuleType enum
│   │   ├── services/               # Business logic layer
│   │   │   ├── auth_service.py     # User registration, JWT, API key auth
│   │   │   ├── account_service.py  # Ad account connect/disconnect logic
│   │   │   ├── campaign_service.py # Campaign CRUD + plan limit checks
│   │   │   ├── creative_service.py # Creative CRUD + AI copy generation (mock)
│   │   │   ├── metrics_service.py  # Aggregation (ROAS, CPA, CTR)
│   │   │   ├── optimization_service.py # Rule evaluation + execution engine
│   │   │   └── billing_service.py  # Stripe checkout, portal, usage
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── auth.py             # Register, login, token, provision schemas
│   │   │   ├── ads.py              # Ad account, campaign, ad group, creative, metrics, rule schemas
│   │   │   └── billing.py          # Plan, checkout, subscription, usage schemas
│   │   ├── constants/
│   │   │   └── plans.py            # Plan tier limits + Stripe price ID binding
│   │   └── utils/
│   │       └── helpers.py          # Shared utility functions
│   ├── tests/                      # 77 backend tests
│   │   ├── conftest.py             # Fixtures: async client, DB setup/teardown, auth helpers
│   │   ├── test_auth.py            # 11 tests: register, login, refresh, profile
│   │   ├── test_accounts.py        # 15 tests: connect, list, disconnect, isolation
│   │   ├── test_campaigns.py       # 20 tests: CRUD, pagination, ownership, limits
│   │   ├── test_creatives.py       # 16 tests: CRUD, chain ownership, AI generation
│   │   ├── test_rules.py           # 20+ tests: CRUD, execute-now, isolation
│   │   ├── test_billing.py         # 9 tests: plans, checkout, overview, subscriptions
│   │   ├── test_api_keys.py        # 5 tests: create, list, revoke, auth
│   │   └── test_health.py          # 1 test: health check
│   └── alembic/                    # Database migrations
├── dashboard/
│   ├── src/
│   │   ├── service.config.ts       # Single source of truth: name, colors, nav, plans
│   │   ├── app/
│   │   │   ├── layout.tsx          # Root layout with sidebar + top bar
│   │   │   ├── page.tsx            # Dashboard home (overview)
│   │   │   ├── campaigns/page.tsx  # Campaign management page
│   │   │   ├── creatives/page.tsx  # Creative management page
│   │   │   ├── analytics/page.tsx  # Analytics dashboard page
│   │   │   ├── billing/page.tsx    # Billing + plan management
│   │   │   ├── api-keys/page.tsx   # API key management
│   │   │   ├── settings/page.tsx   # User settings
│   │   │   ├── login/page.tsx      # Login page
│   │   │   └── register/page.tsx   # Registration page
│   │   ├── lib/
│   │   │   ├── api.ts              # Typed API client with token management
│   │   │   ├── auth.ts             # Auth context + hooks
│   │   │   └── utils.ts            # Shared utility functions
│   │   └── components/
│   │       ├── sidebar.tsx          # Config-driven sidebar navigation
│   │       ├── top-bar.tsx          # Header bar with user menu
│   │       ├── shell.tsx            # Page shell wrapper
│   │       ├── motion.tsx           # Animation primitives
│   │       └── ui/                  # Reusable UI components (button, card, input, etc.)
│   └── next.config.ts
└── landing/
    ├── src/
    │   ├── landing.config.ts       # Landing page configuration
    │   ├── app/
    │   │   ├── page.tsx            # Homepage
    │   │   ├── layout.tsx          # Root layout
    │   │   └── pricing/page.tsx    # Pricing page
    │   └── components/
    │       ├── hero.tsx            # Hero section
    │       ├── features.tsx        # Feature highlights
    │       ├── how-it-works.tsx    # How it works section
    │       ├── pricing-cards.tsx   # Pricing tier cards
    │       ├── stats-bar.tsx       # Stats display bar
    │       ├── cta.tsx             # Call-to-action section
    │       ├── navbar.tsx          # Navigation bar
    │       └── footer.tsx          # Footer
    └── next.config.ts
```

---

## Testing

### Running Tests

```bash
# Run all 77 backend tests
make test-backend

# Run with verbose output
cd backend && pytest -v

# Run a specific test file
cd backend && pytest tests/test_campaigns.py -v

# Run a specific test
cd backend && pytest tests/test_campaigns.py::test_create_campaign_success -v
```

### Test Architecture

- **Framework:** pytest + pytest-asyncio
- **HTTP Client:** httpx.AsyncClient (app-level, no server needed)
- **Database:** Uses the same PostgreSQL with `NullPool` for test isolation
- **Isolation:** Tables are `TRUNCATE CASCADE`-d after each test; all non-self DB connections are terminated to prevent deadlocks
- **Auth Helper:** `register_and_login(client, email)` registers a user and returns `{"Authorization": "Bearer <token>"}` headers
- **Chain Helper:** `_setup_chain()` in creative tests creates the full account -> campaign -> ad group chain

### Test Coverage by Module

| Module | Tests | Key Scenarios |
|--------|-------|---------------|
| Auth | 11 | Register, login, refresh, profile, duplicate email, wrong password |
| Ad Accounts | 15 | Connect Google/Meta, duplicate detection (409), list/pagination, disconnect, user isolation |
| Campaigns | 20 | CRUD, all objectives, budget types, plan limits (403), ownership isolation |
| Creatives | 16 | CRUD, chain ownership validation, ad group filtering, AI copy generation |
| Rules | 20+ | CRUD, all rule types, execute-now, threshold evaluation, user isolation |
| Billing | 9 | Plan listing, checkout (mock), overview, subscriptions |
| API Keys | 5 | Create (raw key), list (no raw key), revoke, auth via X-API-Key |
| Health | 1 | Service status check |

---

## API Conventions

### Authentication

All endpoints except `/auth/register`, `/auth/login`, `/billing/plans`, and `/health` require authentication.

- **JWT Bearer:** `Authorization: Bearer <access_token>`
- **API Key:** `X-API-Key: <raw_key>` (for programmatic access)
- **Dual Auth:** The `/usage` and `/auth/provision` endpoints accept both methods

### Request/Response Patterns

- **Create:** `POST /resource` returns `201` with the created resource
- **List:** `GET /resource?offset=0&limit=50` returns `PaginatedResponse { items, total, offset, limit }`
- **Get:** `GET /resource/{id}` returns `200` with the resource or `404`
- **Update:** `PATCH /resource/{id}` with partial JSON body, returns `200` with updated resource
- **Delete:** `DELETE /resource/{id}` returns `204` (no body) or `404`
- **Plan Limit:** Returns `403` with descriptive error message when plan limit is reached

### Error Codes

| Code | Meaning |
|------|---------|
| 400 | Invalid request data or UUID format |
| 401 | Missing or invalid authentication |
| 403 | Plan limit reached |
| 404 | Resource not found or not owned by current user |
| 409 | Conflict (duplicate resource) |
| 422 | Validation error (Pydantic) |

### Ownership Model

Resources form a hierarchical ownership chain validated on every request:

```
User -> Ad Account -> Campaign -> Ad Group -> Creative
User -> Optimization Rule
User -> Campaign Metrics (via Campaign)
```

Ad groups validate ownership through their parent campaign. Creatives validate through the full chain: `creative.ad_group.campaign.user_id == current_user.id`.

---

## Design System

| Property | Value |
|----------|-------|
| Primary Color | Amber Gold -- `oklch(0.72 0.18 80)` / `#f59e0b` |
| Accent Color | Light Amber -- `oklch(0.78 0.15 60)` / `#fbbf24` |
| Heading Font | Anybody |
| Body Font | Manrope |
| Icon Library | lucide-react |

The dashboard is config-driven via `/dashboard/src/service.config.ts`. Changing `name`, `tagline`, `colors`, or `navigation` in that file updates the entire dashboard UI.

---

## Key Models and Enums

### AdPlatform
- `google` -- Google Ads
- `meta` -- Meta (Facebook/Instagram) Ads

### CampaignObjective
- `traffic` -- Drive clicks and website visits
- `conversions` -- Optimize for purchase or signup conversions
- `awareness` -- Maximize impressions and brand visibility
- `sales` -- Optimize for direct product sales (ROAS-focused)

### CampaignStatus
- `draft` -- Being set up, not yet running
- `active` -- Live and delivering ads
- `paused` -- Temporarily stopped by user
- `completed` -- Ended (past end date or budget exhausted)

### BidStrategy
- `manual` -- Manual CPC bidding
- `auto_cpc` -- Automatic CPC
- `target_roas` -- Target ROAS optimization
- `maximize_conversions` -- Maximize conversions within budget

### RuleType (Optimization Actions)
- `pause_low_roas` -- Pause campaigns with ROAS below threshold
- `scale_high_roas` -- Increase budget 20% for campaigns with ROAS above threshold
- `adjust_bid` -- Adjust bid amounts based on performance
- `increase_budget` -- Increase daily budget 15% when performing well

---

## Plan Limits (Enforced at API Layer)

| Resource | Free | Pro ($49/mo) | Enterprise ($149/mo) |
|----------|------|------|------------|
| Campaigns | 2 | 25 | Unlimited (-1) |
| Ad Groups | 5 | 100 | Unlimited (-1) |
| AI Copies/mo | 5 | Unlimited | Priority AI |
| Platforms | 1 | Google + Meta | All + API |
| Auto-Optimize | No | Yes | Yes + ROAS targets |
| API Access | No | Yes | Yes |
| Trial Days | 0 | 14 | 14 |

Plan limits are defined in `backend/app/constants/plans.py` and enforced in `campaign_service.py` (campaigns) and `ad_groups.py` (ad groups).

---

## Service Integration

AdScale integrates with the dropshipping platform via:

1. **User Provisioning:** `POST /auth/provision` creates/links users from the platform (API key auth)
2. **Usage Reporting:** `GET /usage` returns billing-period metrics for the platform billing dashboard
3. **API Key Auth:** Platform uses `X-API-Key` header for server-to-server requests
4. **Webhook Handling:** `POST /webhooks/stripe` processes Stripe subscription events

---

## Platform Event Webhook

### Platform Event Webhook

Each service receives platform events from the dropshipping backend via
`POST /api/v1/webhooks/platform-events`. Events are HMAC-SHA256 signed
using `platform_webhook_secret`. The receiver verifies the signature and
routes events to service-specific handlers.
