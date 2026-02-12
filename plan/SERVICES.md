# Service Products Architecture

## Overview

The dropshipping platform's automation features (A1-A8) are built as **8 independent, separately hostable SaaS products**. Each product has its own backend, dashboard, landing page, database, users, billing, and API.

## Products

| # | Name | Tagline | Backend | Dashboard | Landing |
|---|------|---------|---------|-----------|---------|
| A1 | **TrendScout** | AI-Powered Product Research | :8101 | :3101 | :3201 |
| A2 | **ContentForge** | AI Product Content Generator | :8102 | :3102 | :3202 |
| A3 | **RankPilot** | Automated SEO Engine | :8103 | :3103 | :3203 |
| A4 | **FlowSend** | Smart Email Marketing | :8104 | :3104 | :3204 |
| A5 | **SpyDrop** | Competitor Intelligence | :8105 | :3105 | :3205 |
| A6 | **PostPilot** | Social Media Automation | :8106 | :3106 | :3206 |
| A7 | **AdScale** | AI Ad Campaign Manager | :8107 | :3107 | :3207 |
| A8 | **ShopChat** | AI Shopping Assistant | :8108 | :3108 | :3208 |

## Architecture Principles

1. **Complete Independence**: No shared libraries, databases, or imports between services
2. **Config-Driven**: Dashboard and landing page are customized via config files
3. **Scaffolded from Template**: All services share the same structure but are fully independent
4. **REST API Integration**: Services communicate only via HTTP APIs
5. **Own Billing**: Each service has its own Stripe subscription management

## Directory Structure

```
services/
├── _template/          # Scaffold template (not a service itself)
│   ├── backend/        # FastAPI template
│   ├── dashboard/      # Next.js dashboard template
│   ├── landing/        # Next.js landing page template
│   └── scripts/        # Scaffold script
├── trendscout/         # A1: Product Research
├── contentforge/       # A2: AI Content
├── rankpilot/          # A3: SEO
├── flowsend/           # A4: Email Marketing
├── spydrop/            # A5: Competitor Monitor
├── postpilot/          # A6: Social Media
├── adscale/            # A7: Ad Campaigns
└── shopchat/           # A8: AI Chatbot
```

## Per-Service Architecture

Each service follows the same internal structure:

```
<service>/
├── backend/            # FastAPI + SQLAlchemy + Celery
│   ├── app/
│   │   ├── api/        # Route handlers
│   │   ├── models/     # SQLAlchemy models
│   │   ├── schemas/    # Pydantic schemas
│   │   ├── services/   # Business logic
│   │   ├── tasks/      # Celery tasks
│   │   └── constants/  # Plan limits
│   ├── alembic/        # Database migrations
│   └── tests/          # pytest test suite
├── dashboard/          # Next.js admin UI
│   └── src/
│       ├── service.config.ts  # Branding config
│       ├── app/        # Pages
│       ├── components/ # Shared components
│       └── lib/        # API client, auth
├── landing/            # Static landing page
│   └── src/
│       ├── landing.config.ts  # Content config
│       ├── app/        # Pages
│       └── components/ # Sections
├── docker-compose.yml  # Full standalone stack
├── Makefile            # Dev commands
└── README.md           # Documentation
```

## Common API Endpoints (all services)

```
POST /api/v1/auth/register      — Create account
POST /api/v1/auth/login         — Get JWT tokens
POST /api/v1/auth/refresh       — Refresh tokens
GET  /api/v1/auth/me            — User profile
POST /api/v1/auth/provision     — Platform provisioning
GET  /api/v1/billing/plans      — List pricing tiers
POST /api/v1/billing/checkout   — Start subscription
POST /api/v1/billing/portal     — Manage subscription
GET  /api/v1/billing/overview   — Plan + usage
GET  /api/v1/usage              — Usage metrics (API key auth)
POST /api/v1/api-keys           — Create API key
GET  /api/v1/api-keys           — List API keys
DELETE /api/v1/api-keys/{id}    — Revoke API key
GET  /api/v1/health             — Health check
POST /api/v1/webhooks/stripe    — Stripe webhooks
```

## Platform Integration

The dropshipping platform connects to services via:

1. **User Provisioning**: `POST /api/v1/auth/provision` creates a user in the service
2. **API Key Auth**: Platform stores the returned API key for subsequent calls
3. **Usage Sync**: `GET /api/v1/usage` returns metrics for billing display
4. **Service Proxy**: Dashboard proxies requests through the backend

### Service Integration Models (in dropshipping backend)

- `ServiceIntegration`: Tracks provisioned service accounts per user
- `ServiceUsage`: Caches usage metrics pulled from each service

### Bundle Pricing

| Platform Tier | Included Services | Service Tier |
|---|---|---|
| Free ($0) | None | — |
| Starter ($29) | TrendScout + ContentForge | Free |
| Growth ($79) | All 8 | Free |
| Pro ($199) | All 8 | Pro (saves $264/mo) |

## Scaffolding

```bash
# Create all 8 services at once
./scripts/scaffold-all-services.sh

# Or create one service
./services/_template/scripts/scaffold.sh trendscout "TrendScout" "AI-Powered Product Research" 8101 3101 3201
```

## Implementation Status

- [x] Backend template (auth, billing, API keys, tests)
- [x] Dashboard template (config-driven, shadcn/ui, animations)
- [x] Landing page template (CSS animations, config-driven)
- [x] Infrastructure (docker-compose, Makefile, scaffold script)
- [x] Scaffold all 8 services with unique configs
- [x] TrendScout (A1) — feature routes, models, services, tests (67), dashboard pages (2)
- [x] ContentForge (A2) — feature routes, models, services, tests (45), dashboard pages (2)
- [x] RankPilot (A3) — feature routes, models, services, tests (74), dashboard pages (3)
- [x] FlowSend (A4) — feature routes, models, services, tests (87), dashboard pages (3)
- [x] SpyDrop (A5) — feature routes, models, services, tests (43), dashboard pages (2)
- [x] PostPilot (A6) — feature routes, models, services, tests (62), dashboard pages (3)
- [x] AdScale (A7) — feature routes, models, services, tests (77), dashboard pages (3)
- [x] ShopChat (A8) — feature routes, models, services, tests (88), dashboard pages (3)
- [x] Master landing page (suite showcase, static export, 7 components)
- [x] Platform integration (ServiceIntegration model, API routes, service layer, dashboard pages)

### Metrics

| Component | Count |
|---|---|
| Standalone services | 8 |
| Service feature tests | ~543 |
| Platform integration tests | 152 |
| Total backend tests | 488 |
| Dashboard pages (per service) | 2-3 per service |
| Dashboard pages (platform) | 2 new (services hub + service detail) |
| Master landing page components | 7 |
| Alembic migrations | 14 (including service_integrations) |

### Platform Integration Details

New files added to the dropshipping backend:
- `backend/app/models/service_integration.py` — ServiceIntegration, ServiceName, ServiceTier
- `backend/app/schemas/services.py` — 11 Pydantic schemas
- `backend/app/services/service_integration_service.py` — 9 service functions, catalog, bundles
- `backend/app/api/services.py` — 8 API endpoints under /api/v1/services/
- `backend/alembic/versions/014_add_service_integrations.py` — migration
- `backend/tests/test_services.py` — 35 endpoint tests
- `backend/tests/test_service_schemas.py` — 79 schema validation tests
- `backend/tests/test_service_integration_service.py` — 38 service layer tests

New dashboard pages:
- `dashboard/src/app/stores/[id]/services/page.tsx` — Services Hub (8-card grid)
- `dashboard/src/app/stores/[id]/services/[service]/page.tsx` — Service detail
- Updated sidebar with "AI & Automation" section
