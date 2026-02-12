# AdScale

> AI Ad Campaign Manager

## Overview

AdScale is an independently hostable SaaS product for managing paid advertising campaigns
across Google Ads and Meta (Facebook + Instagram). It provides AI-generated ad copy,
campaign auto-creation from product data, budget management, performance tracking with
ROAS optimization, and automated rules for scaling profitable campaigns. Can be used
standalone or integrated with the dropshipping platform.

**For Developers:**
    Feature logic in `account_service.py` (Google/Meta API), `campaign_service.py`
    (campaign CRUD + budget), `ad_group_service.py` (targeting + bids), and
    `metrics_service.py` (ROAS/CPA calculation). Dashboard is config-driven via
    `dashboard/src/service.config.ts`.

**For Project Managers:**
    AdScale is Feature A7. Fully scaffolded with 77 backend tests and 3 dashboard
    feature pages. Pricing: Free ($0), Pro ($49/mo), Enterprise ($149/mo).

**For QA Engineers:**
    Test ad account connection, campaign CRUD with cascading ad groups, metrics
    aggregation (ROAS, CPA, CTR), optimization rules, date-range filtering, and
    plan limit enforcement.

**For End Users:**
    Launch and scale ad campaigns with AI assistance. Connect your Google and Meta ad
    accounts, generate compelling ad copy automatically, set budget targets, and let
    auto-optimization rules maximize your return on ad spend.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 | 8107 |
| Dashboard | Next.js 16 + Tailwind | 3107 |
| Landing Page | Next.js 16 (static) | 3207 |
| Database | PostgreSQL 16 | 5507 |
| Cache/Queue | Redis 7 | 6407 |
| Task Queue | Celery | — |

## Quick Start

```bash
make install && make migrate && make start
```

### Access Points
- **API**: http://localhost:8107 | **Docs**: http://localhost:8107/docs
- **Dashboard**: http://localhost:3107
- **Landing Page**: http://localhost:3207

## Core Features

### Ad Account Management
- Connect Google Ads and Meta (Facebook + Instagram) ad accounts
- Encrypted credential storage
- Per-account status tracking and sync

### Campaign Management
- Full campaign CRUD with objective, budget (daily/lifetime), and status
- Campaign auto-creation from product data
- Cascading delete: removing a campaign removes its ad groups
- Platform-specific campaign configuration

### Ad Groups
- Create ad groups within campaigns with targeting and bid strategies
- Audience targeting configuration
- Budget distribution across ad groups

### Performance Metrics
- Aggregate metrics: spend, revenue, ROAS, CTR, CPA, impressions, clicks, conversions
- Per-campaign daily metrics breakdown
- Date-range queries across all campaigns
- Auto-optimization rules: pause low-ROAS, scale profitable, adjust bids

### AI Ad Copy
- Claude API for headline, description, and CTA generation
- Platform-specific copy optimization (Google vs. Meta format)

## API Endpoints

### Ad Accounts
```
POST   /api/v1/accounts                  — Connect ad account (Google Ads / Meta)
GET    /api/v1/accounts                  — List ad accounts
DELETE /api/v1/accounts/{account_id}     — Disconnect account
```

### Campaigns
```
POST   /api/v1/campaigns                 — Create campaign (enforces plan limits)
GET    /api/v1/campaigns                 — List campaigns with pagination
GET    /api/v1/campaigns/{campaign_id}   — Campaign details
PATCH  /api/v1/campaigns/{campaign_id}   — Update campaign
DELETE /api/v1/campaigns/{campaign_id}   — Delete campaign + cascade ad groups
```

### Ad Groups
```
POST   /api/v1/ad-groups                 — Create ad group (enforces plan limits)
GET    /api/v1/ad-groups                 — List with optional campaign filter
GET    /api/v1/ad-groups/{ad_group_id}   — Ad group details
PATCH  /api/v1/ad-groups/{ad_group_id}   — Update ad group
DELETE /api/v1/ad-groups/{ad_group_id}   — Delete ad group
```

### Metrics
```
GET /api/v1/metrics/overview                    — Aggregated metrics (spend, revenue, ROAS, CTR, CPA)
GET /api/v1/metrics/campaign/{campaign_id}      — Daily metrics for campaign
GET /api/v1/metrics/date-range                  — Metrics within date range across all campaigns
```

## Pricing

| Tier | Price/mo | Campaigns | Platforms | AI Copy | Auto-Optimize |
|------|----------|-----------|-----------|---------|---------------|
| Free | $0 | 2 | 1 | 5/mo | No |
| Pro | $49 | 25 | Google + Meta | Unlimited | Yes + ROAS tracking |
| Enterprise | $149 | Unlimited | All + API | Priority AI | Yes + ROAS targets + Dedicated |

## Database Tables

| Table | Purpose |
|-------|---------|
| `users`, `api_keys`, `subscriptions` | Auth & billing (standard) |
| `ad_accounts` | Connected ad platforms with encrypted credentials |
| `campaigns` | Ad campaigns with objective, budget, status |
| `ad_groups` | Ad groups within campaigns (targeting, bids) |
| `campaign_metrics` | Daily performance metrics (impressions, clicks, ROAS, CPA) |
| `optimization_rules` | Auto-optimization rules (pause low-ROAS, scale high-ROAS) |

## Testing

```bash
make test-backend    # 77 backend unit tests
```

## Design System

- **Primary**: Amber Gold — `oklch(0.72 0.18 80)` / `#f59e0b`
- **Accent**: Light Amber — `oklch(0.78 0.15 60)` / `#fbbf24`
- **Heading font**: Inter Tight (business, metrics-focused)
- **Body font**: Inter

## License

Proprietary — All rights reserved.
