# SpyDrop Documentation

> **SpyDrop** is a Competitor Intelligence SaaS service that monitors competitor stores, tracks product catalogs and price changes, sends configurable alerts on significant changes, and performs reverse source-finding to identify original suppliers.

---

## Quick Start

```bash
# From /workspaces/ecomm/spydrop/
make install     # Install Python + Node dependencies
make migrate     # Run Alembic migrations
make start       # Start all services (backend, dashboard, landing)
```

**Access Points:**
- Backend API: http://localhost:8105
- API Docs (Swagger): http://localhost:8105/docs
- Dashboard: http://localhost:3105
- Landing Page: http://localhost:3205

---

## Documentation

| Guide | Audience | Content |
|-------|----------|---------|
| [Setup](SETUP.md) | Developers | Local dev environment, prerequisites, ports, environment variables |
| [Architecture](ARCHITECTURE.md) | Developers | Tech stack, project structure, database schema, design decisions |
| [API Reference](API_REFERENCE.md) | Developers & QA | Endpoint documentation, request/response formats, conventions |
| [Testing](TESTING.md) | Developers & QA | Test infrastructure, running tests, coverage, writing tests |
| [Project Manager](PROJECT_MANAGER.md) | PMs | Status, metrics, pricing, timeline, integration, risks |
| [QA Engineer](QA_ENGINEER.md) | QA | Acceptance criteria, verification checklists, edge cases |
| [End User](END_USER.md) | End Users | Features, workflows, subscription tiers, getting started |
| [Implementation Steps](IMPLEMENTATION_STEPS.md) | Developers | Step-by-step implementation history (template to production) |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Backend Tests | **156 passing** (6 test files) |
| Dashboard Pages | **8 pages** (home, competitors, products, billing, API keys, settings, login, register) |
| API Endpoints | **20+ endpoints** across 8 route modules |
| Database Models | **8 models** (User, Subscription, ApiKey, Competitor, CompetitorProduct, PriceAlert, AlertHistory, ScanResult, SourceMatch) |
| Service Ports | Backend: 8105, Dashboard: 3105, Landing: 3205, DB: 5505, Redis: 6405 |

---

## Service Overview

SpyDrop automates competitor intelligence for dropshippers and e-commerce sellers with:

- **Competitor Monitoring** — Add competitor store URLs and scan them automatically
- **Product Tracking** — Discover products, track price history with JSON-based timeline storage
- **Price Alerts** — 5 alert types (price drop/increase, new product, out of stock, back in stock)
- **Reverse Source Finding** — Match competitor products to suppliers (AliExpress, DHgate, etc.) with confidence scoring
- **Cross-Service Integration** — API-based provisioning from the dropshipping platform

---

## Subscription Tiers

| Tier | Price | Competitors | Scan Frequency | Products | Alerts | Source Finding | API |
|------|-------|-------------|----------------|----------|--------|----------------|-----|
| **Free** | $0 | 3 | Weekly | 50 | No | No | No |
| **Pro** | $29 | 25 | Daily | 2,500 | Yes | Yes | Yes |
| **Enterprise** | $99 | Unlimited | Hourly | Unlimited | Yes + API | Yes + Bulk | Yes |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
