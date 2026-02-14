# Project Manager Guide

**For Project Managers:** TrendScout is an AI-powered product research SaaS product (Feature A1 in the platform roadmap). It discovers trending, high-potential products using multi-source data aggregation and AI-powered scoring. TrendScout is fully scaffolded with authentication, billing, API keys, 158 backend tests, 8 dashboard pages, and 2 landing pages. It can be sold as a standalone SaaS product or integrated with the dropshipping platform as an add-on service.

---

## Project Overview

TrendScout helps e-commerce entrepreneurs find winning products before their competitors by:

1. **Aggregating data from multiple sources** -- AliExpress, TikTok, Google Trends, and Reddit
2. **Scoring products with a weighted AI algorithm** across 5 dimensions (Social, Market, Competition, SEO, Fundamentals)
3. **Running deep AI analysis** via Claude to assess opportunity, risk, pricing, audience, and marketing angles
4. **Managing a watchlist** of promising products for import into the user's store

The product targets dropshipping sellers, e-commerce store owners, and product researchers who want data-driven product discovery.

---

## Key Differentiators

| Differentiator | Description |
|---------------|-------------|
| **Multi-Source Research** | Aggregates data from 4 sources (AliExpress, TikTok, Google Trends, Reddit) in a single run |
| **AI-Powered Scoring** | Weighted composite score (0-100) across 5 dimensions with customizable weights |
| **Deep AI Analysis** | Claude-powered insights: opportunity score, risk factors, pricing, audience, marketing angles |
| **Watchlist Management** | Save, annotate, and track products through watching/imported/dismissed states |
| **Standalone + Integrated** | Works as independent SaaS or as a platform add-on via the provision API |
| **Plan-Gated Features** | Tiered access (Free/Pro/Enterprise) with enforced resource limits |

---

## Architecture Summary

| Component | Port | Purpose | Pages/Endpoints |
|-----------|------|---------|----------------|
| Backend API | 8101 | FastAPI REST API for all business logic | 22+ endpoints across 7 route groups |
| Dashboard | 3101 | Next.js user interface for research and management | 8 pages (home, research, watchlist, billing, API keys, settings, login, register) |
| Landing Page | 3201 | Next.js static marketing site | 2 pages (hero + features, pricing) |
| PostgreSQL | 5501 | Data persistence | 7 tables |
| Redis | 6401 | Caching + Celery task broker | -- |
| Celery Worker | -- | Background research task execution | 1 task (run_research) |

---

## Current Status

### Completed

- Service template scaffolding (all shared infrastructure: auth, billing, API keys, health)
- TrendScout feature models (research_runs, research_results, watchlist_items, source_configs)
- Feature services (research_service, scoring_service, ai_analysis_service)
- Feature API routes (research.py, watchlist.py, sources.py)
- Feature tests (158 backend tests across 7 test files)
- Dashboard pages (8 pages: home, research, watchlist, billing, API keys, settings, login, register)
- Landing page (2 pages: hero/features, pricing)
- Celery background task with mock data generators for all 4 sources
- Stripe billing integration (mock mode for development, real Stripe for production)
- Cross-platform provisioning API for dropshipping platform integration

### Pending / Future Work

- Dashboard "Sources" and "History" pages (navigation defined but pages not yet created)
- Real API integrations for AliExpress (Apify), TikTok (Apify), Google Trends (pytrends), Reddit (PRAW)
- Playwright E2E tests for the dashboard
- Production Stripe Price ID configuration
- Production Anthropic API key for real Claude analysis
- Email notifications (password reset, research run completed)
- CSV export of research results

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Backend Tests | 158 |
| Dashboard Pages | 8 |
| Landing Pages | 2 |
| API Endpoints | 22+ |
| Database Models | 7 (User, Subscription, ApiKey, ResearchRun, ResearchResult, WatchlistItem, SourceConfig) |
| Database Tables | 7 |
| Service Files | 5 (auth, billing, research, scoring, AI analysis) |
| API Route Modules | 7 (auth, billing, research, watchlist, sources, api_keys, deps) |
| Schema Files | 3 (auth, billing, research) |
| Task Files | 2 (celery_app, research_tasks) |
| Scoring Dimensions | 5 (Social, Market, Competition, SEO, Fundamentals) |
| Data Sources | 4 (AliExpress, TikTok, Google Trends, Reddit) |

---

## Pricing Tiers

| Tier | Price/Month | Research Runs | Data Sources | AI Analysis | Watchlist Items | API Access | Trial Days |
|------|-------------|--------------|--------------|-------------|-----------------|------------|-----------|
| Free | $0 | 5/month | 2 (AliExpress + Google Trends) | Basic scoring | 25 | No | 0 |
| Pro | $29 | 50/month | All 4 + custom | Full AI analysis | 500 | Yes | 14 |
| Enterprise | $99 | Unlimited | All sources + API | Priority processing | Unlimited | Yes | 14 |

### Revenue Model

- **Free tier** drives user acquisition and product awareness
- **Pro tier** ($29/mo) is the primary revenue driver for individual sellers
- **Enterprise tier** ($99/mo) targets agencies and high-volume sellers with unlimited access and dedicated support

---

## Tech Stack Overview

| Category | Technology |
|----------|-----------|
| Backend Language | Python 3.12 |
| Backend Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| Task Queue | Celery |
| Migrations | Alembic |
| Frontend Framework | Next.js 16 (App Router) |
| CSS | Tailwind CSS |
| Auth | JWT (python-jose) + bcrypt |
| Billing | Stripe (with mock mode) |
| AI | Anthropic Claude API |
| Testing | pytest, pytest-asyncio, httpx |

---

## Integration with Dropshipping Platform

TrendScout integrates with the main dropshipping platform through:

1. **Provision API** (`POST /api/v1/auth/provision`): The platform creates/links TrendScout accounts for its users, assigning a plan tier and receiving an API key for subsequent requests.

2. **API Key Authentication** (`X-API-Key` header): The platform uses provisioned API keys to access TrendScout endpoints on behalf of users.

3. **External ID Linking**: Each provisioned user stores `external_platform_id` and `external_store_id` for cross-platform identity mapping.

4. **No Shared Database**: TrendScout maintains its own independent database. All communication is via HTTP REST API.

5. **Watchlist to Store Import**: Users can mark watchlist items as "imported" after pushing products to their dropshipping store (the actual import integration is handled at the platform level).

---

## Key Documents

| Document | Path | Description |
|----------|------|-------------|
| Service README | `trendscout/README.md` | Service overview, quick start, API reference |
| Developer Guide | `trendscout/docs/DEVELOPER.md` | Setup, architecture, conventions |
| QA Engineer Guide | `trendscout/docs/QA_ENGINEER.md` | Testing procedures, coverage, verification |
| End User Guide | `trendscout/docs/END_USER.md` | Feature guide for end users |
| Implementation Steps | `trendscout/docs/IMPLEMENTATION_STEPS.md` | Step-by-step build history |
| Service Config | `trendscout/dashboard/src/service.config.ts` | Branding, navigation, plans |
| Plan Constants | `trendscout/backend/app/constants/plans.py` | Plan limits and Stripe mapping |
| Platform Architecture | `plan/ARCHITECTURE.md` | Overall platform architecture |
| Platform Backlog | `plan/BACKLOG.md` | Feature backlog and roadmap |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| External API rate limits (AliExpress, TikTok) | Medium -- research runs may fail or return fewer results | High | Implement retry logic, caching, and user-facing rate limit warnings |
| Claude API costs at scale | Medium -- AI analysis is the most expensive per-result operation | Medium | Limit AI analysis to Pro/Enterprise tiers; batch requests; cache repeated queries |
| Stripe webhook delivery failures | High -- subscriptions may not sync correctly | Low | Implement webhook retry handling; add manual subscription sync admin endpoint |
| Mock-to-real API transition | Medium -- mock data differs from real source structure | Medium | Design source adapters with consistent output schema; test with real APIs early |
| Data source API deprecation | High -- loss of a data source reduces product coverage | Low | Modular source architecture allows quick replacement; monitor API changelogs |
| User data security (source credentials) | Critical -- leaked API keys could compromise user accounts | Low | Credentials stored encrypted; never returned in API responses; has_credentials flag only |
| Plan limit bypass | Medium -- users could exploit edge cases to exceed limits | Low | Limits enforced at service layer with atomic count checks; tested in unit tests |
| Celery worker downtime | Medium -- research runs stuck in "pending" state | Medium | Health monitoring; auto-restart; user-facing retry mechanism for stuck runs |
