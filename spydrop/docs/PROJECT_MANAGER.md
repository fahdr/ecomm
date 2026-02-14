# Project Manager Guide

**For Project Managers:** SpyDrop is the Competitor Intelligence service (Feature A5) in the dropshipping platform ecosystem. It enables users to monitor competitor stores, track product catalogs and price changes, receive automated alerts, and perform reverse source-finding to identify original suppliers.

---

## Overview

SpyDrop solves a critical problem for dropshippers: staying ahead of the competition. Instead of manually checking competitor stores for new products and price changes, SpyDrop automates the entire process with scheduled scanning, change detection, alerting, and supplier identification.

### Key Differentiators

1. **Playwright-powered scraping:** Uses headless browser automation to scan real competitor stores (Shopify, WooCommerce, and custom platforms), extracting product catalogs, prices, and availability data that simple HTTP scraping cannot access.

2. **Price history tracking:** Every product scan appends to a JSON-based price history timeline, giving users a complete view of how competitor pricing has changed over days, weeks, and months. The dashboard renders mini bar charts and detailed history dialogs.

3. **Reverse source finding:** Matches competitor products to potential suppliers (AliExpress, DHgate, 1688, Alibaba, Banggood, etc.) using image search and title matching with confidence scoring. Calculates potential profit margins automatically.

4. **Configurable alert system:** Five alert types (price drop, price increase, new product, out of stock, back in stock) with customizable thresholds. Alerts are evaluated automatically after each scan and stored in a queryable history.

5. **Cross-service integration:** Users can be provisioned from the dropshipping platform via API, enabling seamless single-click activation from the platform dashboard.

---

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 (async) | 8105 |
| Dashboard | Next.js 16 (App Router) + Tailwind | 3105 |
| Landing Page | Next.js 16 (static) | 3205 |
| Database | PostgreSQL 16 | 5505 |
| Cache / Queue | Redis 7 | 6405 |
| Task Queue | Celery | -- |
| Scraping Engine | Playwright (headless) | -- |

The backend is a standalone FastAPI application with its own database, independent from the main dropshipping platform. Communication with the platform happens via HTTP API (provisioning endpoint + API key authentication).

---

## Current Status

| Metric | Value |
|--------|-------|
| Backend tests | **43 passing** (6 test files) |
| Dashboard pages | **8 pages** (home, competitors, products, billing, API keys, settings, login, register) |
| API endpoints | **20+ endpoints** across 8 route modules |
| Database models | **8 models** (User, Subscription, ApiKey, Competitor, CompetitorProduct, PriceAlert, AlertHistory, ScanResult, SourceMatch) |
| Database tables | **~10 tables** (including Alembic version) |
| Service status | Fully scaffolded, core features implemented, ready for demo |

### What Is Complete

- User registration, login, JWT authentication, API key management
- Competitor CRUD with plan limit enforcement
- Product tracking with price history
- Cross-competitor product browsing with filters and sorting
- Alert model and triggering logic (5 alert types)
- Scan engine (mock data for demo; Playwright integration planned)
- Source matching engine (mock supplier data with confidence scoring)
- Stripe billing integration (mock mode for development)
- Dashboard with animated UI (competitors table, product grid, price history dialog)
- Landing page (static marketing site)

### What Needs Production Work

- Replace mock scan engine with real Playwright scraping
- Replace mock source matching with real supplier API integrations
- Configure real Stripe API keys and webhook endpoints
- Set up Celery beat for scheduled scans per plan tier
- Add email delivery for triggered alerts
- Add alert management dashboard pages (CRUD UI)
- Add scan history dashboard page
- Add source matches dashboard page

---

## Metrics Summary

| Category | Detail |
|----------|--------|
| Test coverage | 43 backend tests across auth, competitors, products, billing, API keys, health |
| Dashboard pages | 8 implemented pages with full CRUD flows |
| API surface | Auth (6), Competitors (6), Products (2), Billing (5), API Keys (3), Usage (1), Webhooks (1), Health (1) |
| Models | 8 domain models + 2 enums (PlanTier, SubscriptionStatus) |
| Services | 6 service modules (auth, competitor, scan, alert, source, billing) |

---

## Pricing

| Tier | Monthly Price | Competitor Stores | Scan Frequency | Products Tracked | Price Alerts | Source Finding | API Access | Trial |
|------|-------------|------------------|----------------|-----------------|--------------|----------------|------------|-------|
| **Free** | $0 | 3 | Weekly | 50 | No | No | No | -- |
| **Pro** | $29 | 25 | Daily | 2,500 | Yes | Yes | Yes | 14 days |
| **Enterprise** | $99 | Unlimited | Hourly | Unlimited | Yes + API | Yes + Bulk | Yes | 14 days |

Plan limits are enforced at the API layer. The `PLAN_LIMITS` constant in `backend/app/constants/plans.py` defines the exact limits for each tier. The competitor creation endpoint checks the user's current plan before allowing new competitors.

### Revenue Projections

- Free tier serves as user acquisition funnel
- Pro at $29/mo is the target conversion tier for active dropshippers
- Enterprise at $99/mo targets agencies and power users with high volume needs
- 14-day free trial on paid plans reduces friction for conversion

---

## Integration with Dropshipping Platform

SpyDrop integrates with the main dropshipping platform through:

1. **User provisioning:** `POST /api/v1/auth/provision` creates a SpyDrop user account linked to the platform user, with an API key for subsequent calls. The platform calls this when a user activates the SpyDrop service.

2. **Usage reporting:** `GET /api/v1/usage` returns current usage metrics (competitors used, products tracked) in a standardized format. The platform polls this to display aggregated service usage on its billing dashboard.

3. **API key authentication:** All provisioned integrations authenticate via `X-API-Key` header, allowing the platform to make requests on behalf of users without managing JWTs.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Competitor sites block scraping | High | High | Rotate IPs, use residential proxies, respect robots.txt, implement retry with backoff |
| Playwright memory usage at scale | Medium | High | Run scans in isolated containers, implement concurrency limits per tier |
| Stripe webhook delivery failures | Low | Medium | Implement webhook retry queue, reconciliation job, manual sync endpoint |
| Price history data growth | Medium | Medium | Implement retention policies (e.g., daily rollup after 90 days), archive old data |
| False positive source matches | High | Medium | Display confidence scores prominently, allow users to dismiss bad matches |
| Plan limit bypass attempts | Low | Low | Server-side enforcement in service layer, not just UI gates |
| Database deadlocks during scans | Low | Medium | Use optimistic locking, scan in separate transaction, terminate idle connections |

---

## Timeline and Milestones

### Phase 1: Core Platform (COMPLETE)
- User auth, competitor CRUD, product tracking, billing
- Dashboard with competitors and products pages
- 43 backend tests passing

### Phase 2: Production Scraping (NEXT)
- Replace mock scan engine with Playwright
- Implement Shopify, WooCommerce, and custom platform parsers
- Set up Celery beat for scheduled scans
- Configure real Stripe billing

### Phase 3: Intelligence Features
- Real supplier API integrations for source matching
- Email notification delivery for alerts
- Alert management UI in dashboard
- Scan history timeline page

### Phase 4: Scale and Polish
- IP rotation and proxy infrastructure
- Performance optimization for high-volume users
- Data retention and archival policies
- Analytics dashboard for competitive insights
