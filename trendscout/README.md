# TrendScout

> AI-Powered Product Research

## Overview

TrendScout is an independently hostable SaaS product that discovers trending, high-potential
products using multi-source data aggregation and AI-powered scoring. It can be used
standalone or integrated with the dropshipping platform as an add-on service.

**For Developers:**
    TrendScout follows the standard service template (FastAPI + SQLAlchemy 2.0 async + Celery).
    Feature logic lives in `backend/app/services/research_service.py` and
    `backend/app/services/scoring_service.py`. The dashboard is config-driven via
    `dashboard/src/service.config.ts`.

**For Project Managers:**
    TrendScout is Feature A1 in the platform roadmap. It is fully scaffolded with
    auth, billing, API keys, 67 backend tests, and 2 dashboard feature pages.
    Pricing: Free ($0), Pro ($29/mo), Enterprise ($99/mo).

**For QA Engineers:**
    Test the research run lifecycle (create → poll status → view results), watchlist
    CRUD, source configuration, and plan limit enforcement. 67 tests cover auth,
    billing, research, watchlist, and source endpoints.

**For End Users:**
    Discover winning products before your competitors. Set up data sources, run AI-powered
    research, and save promising finds to your watchlist for import into your store.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 | 8101 |
| Dashboard | Next.js 16 + Tailwind | 3101 |
| Landing Page | Next.js 16 (static) | 3201 |
| Database | PostgreSQL 16 | 5501 |
| Cache/Queue | Redis 7 | 6401 |
| Task Queue | Celery | — |

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 16
- Redis 7

### Local Development

```bash
# Install dependencies
make install

# Run database migrations
make migrate

# Start all services
make start
```

### Docker

```bash
docker-compose up
```

### Access Points
- **API**: http://localhost:8101
- **API Docs**: http://localhost:8101/docs
- **Dashboard**: http://localhost:3101
- **Landing Page**: http://localhost:3201

## Core Features

### Research Engine
- **Multi-source data aggregation**: AliExpress, TikTok (Apify), Google Trends (pytrends), Reddit (PRAW)
- **AI scoring algorithm**: Weighted composite score (social 40%, market 30%, competition 15%, SEO 10%, fundamentals 5%)
- **Claude API analysis**: Deep product viability assessment with market insights
- **Async processing**: Research runs execute via Celery tasks with real-time status polling

### Watchlist Management
- Save promising research results for later review
- Status tracking: watching → imported → dismissed
- Notes and annotations per item
- Plan-enforced limits (Free: 25 items, Pro: 500, Enterprise: unlimited)

### Source Configuration
- Per-user API credential management for each data source
- Enable/disable individual sources per run
- Custom source settings and refresh intervals

## API Endpoints

### Authentication (standard across all services)
```
POST /api/v1/auth/register       — Create account
POST /api/v1/auth/login          — Get JWT tokens
POST /api/v1/auth/refresh        — Refresh tokens
GET  /api/v1/auth/me             — User profile
POST /api/v1/auth/provision      — Platform provisioning
```

### Billing (standard across all services)
```
GET  /api/v1/billing/plans       — List pricing tiers
POST /api/v1/billing/checkout    — Start Stripe subscription
POST /api/v1/billing/portal      — Manage subscription
GET  /api/v1/billing/overview    — Plan + usage summary
```

### Research (feature-specific)
```
POST /api/v1/research/runs                — Create research run (dispatches Celery task)
GET  /api/v1/research/runs                — List runs with pagination
GET  /api/v1/research/runs/{run_id}       — Get run details with results
DELETE /api/v1/research/runs/{run_id}     — Delete run and results
GET  /api/v1/research/results/{result_id} — Get single research result
```

### Watchlist
```
POST   /api/v1/watchlist                  — Add result to watchlist
GET    /api/v1/watchlist                  — List watchlist items (filterable by status)
PATCH  /api/v1/watchlist/{item_id}        — Update status/notes
DELETE /api/v1/watchlist/{item_id}        — Remove from watchlist
```

### Sources
```
POST   /api/v1/sources                    — Create source config
GET    /api/v1/sources                    — List source configs
PATCH  /api/v1/sources/{config_id}        — Update credentials/settings
DELETE /api/v1/sources/{config_id}        — Delete source config
```

### API Keys & Usage
```
POST   /api/v1/api-keys                  — Create API key
GET    /api/v1/api-keys                  — List API keys
DELETE /api/v1/api-keys/{id}             — Revoke API key
GET    /api/v1/usage                     — Usage metrics (API key auth)
GET    /api/v1/health                    — Health check
```

## API Authentication

### JWT Bearer Token
```bash
# Register
curl -X POST http://localhost:8101/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Use token
curl http://localhost:8101/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### API Key
```bash
# Create API key (requires JWT auth)
curl -X POST http://localhost:8101/api/v1/api-keys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Integration", "scopes": ["read", "write"]}'

# Use API key
curl http://localhost:8101/api/v1/usage \
  -H "X-API-Key: <api_key>"
```

## Pricing

| Tier | Price/mo | Research Runs | Data Sources | AI Analysis | Watchlist Items |
|------|----------|--------------|--------------|-------------|-----------------|
| Free | $0 | 5/mo | 2 (AliExpress + Trends) | Basic scoring | 25 |
| Pro | $29 | 50/mo | All 4 + custom | Full AI analysis | 500 |
| Enterprise | $99 | Unlimited | All sources + API | Priority processing | Unlimited |

## Database Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts (email, password, plan, Stripe) |
| `api_keys` | API key management |
| `subscriptions` | Stripe subscription state |
| `research_runs` | Research job tracking (keywords, sources, status) |
| `research_results` | Individual product results with scores and AI analysis |
| `watchlist_items` | Saved results for review/import |
| `source_configs` | Per-user data source credentials and settings |

## Testing

```bash
make test-backend    # 67 backend unit tests
```

Test coverage includes: auth flow, billing lifecycle, research run CRUD, watchlist management,
source configuration, plan limit enforcement, and API key operations.

## Design System

- **Primary color**: Electric Blue — `oklch(0.65 0.20 250)` / `#3b82f6`
- **Accent color**: Cyan — `oklch(0.75 0.15 200)` / `#38bdf8`
- **Heading font**: Space Grotesk (technical, data-driven feel)
- **Body font**: Inter

## Environment Variables

See `.env.example` for all available configuration options.

## License

Proprietary — All rights reserved.
