# SourcePilot -- Project Manager Documentation

## Product Summary

**SourcePilot** is an automated supplier product import service for dropshipping merchants. It bridges the gap between supplier platforms (AliExpress, CJ Dropshipping, Spocket) and the merchant's own e-commerce store, enabling one-click product imports, price monitoring, and bulk operations.

**Target users**: Dropshipping merchants who source products from multiple supplier platforms and need to efficiently import them into Shopify, WooCommerce, or other e-commerce stores.

---

## Feature Scope

### Core Features

| Feature | Status | Description |
|---|---|---|
| **Product Import** | Complete | Import products from supplier URLs into connected stores. Supports single and bulk (up to 50 URLs) imports. Background processing via Celery. |
| **Product Search** | Complete (Mock) | Search supplier catalogs by keyword. Returns paginated results with product previews. Currently uses mock data; production will call real supplier APIs. |
| **Product Preview** | Complete (Mock) | Preview detailed product information before importing. Auto-detects supplier from URL domain. Results cached for 24 hours. |
| **Supplier Accounts** | Complete | Connect and manage supplier platform credentials (AliExpress, CJ Dropshipping, Spocket). CRUD operations with duplicate detection. |
| **Store Connections** | Complete | Connect dropshipping stores as import targets. Default store management (auto-set first, promote on delete). Supports Shopify, WooCommerce. |
| **Price Watch** | Complete (Mock) | Monitor supplier product prices. Manual and automatic sync. Configurable alert thresholds (default 10%). Currently uses mock pricing. |
| **Import History** | Complete | Full audit trail for every import job lifecycle event (created, retried, cancelled, failed). |
| **Authentication** | Complete | Email/password registration, JWT token-based auth, token refresh, API key access for integrations. |
| **Billing** | Complete | Stripe integration with Free/Pro/Enterprise tiers. Mock mode for development. Checkout, portal, usage tracking. |
| **Cross-Service Integration** | Complete | User provisioning from the dropshipping platform. TrendScout webhook for auto-importing high-scoring products. |
| **API Keys** | Complete | Programmatic access via API keys. Create, list, revoke. SHA-256 hashed storage. |

### Dashboard Pages

| Page | Route | Description |
|---|---|---|
| Dashboard Home | `/` | KPI cards (imports this month, price watches, connected stores, plan), quick action buttons |
| Imports | `/imports` | Create new imports, view history, cancel/retry jobs |
| Products | `/products` | Search supplier catalogs, preview products before import |
| Suppliers | `/suppliers` | Manage supplier platform accounts and credentials |
| Connections | `/connections` | Connect/disconnect stores, set default import target |
| Price Watch | `/price-watch` | Monitor supplier prices, trigger manual sync |
| Billing | `/billing` | View plans, manage subscription, see usage |
| API Keys | `/api-keys` | Create and manage programmatic access keys |
| Settings | `/settings` | Account settings |
| Login | `/login` | User authentication |
| Register | `/register` | New account creation |

---

## Billing Plans

| Plan | Price | Import Limit | Price Watches | Trial | API Access |
|---|---|---|---|---|---|
| **Free** | $0/mo | 10 per month | 25 | None | No |
| **Pro** | $29/mo | 100 per month | 500 | 14 days | Yes |
| **Enterprise** | $99/mo | Unlimited | Unlimited | 14 days | Yes |

**Metering**: Import jobs per billing month is the primary resource. Price watches is the secondary resource. Limits are enforced at the API layer before job creation.

---

## Dependencies

### Internal Dependencies

| Dependency | Purpose |
|---|---|
| **ecomm_core** (shared package) | Authentication, billing, database utilities, health checks, testing helpers |
| **ecomm_connectors** (shared package) | Shopify and WooCommerce platform adapters |
| **LLM Gateway** (port 8200) | Centralized AI provider routing (configured but not yet integrated) |
| **Dropshipping Platform** | Cross-service user provisioning, store connection references |
| **TrendScout** | Product scoring webhook -- auto-imports products scoring >= 50 |

### External Dependencies

| Dependency | Purpose |
|---|---|
| **PostgreSQL** | Primary database (schema: `sourcepilot`) |
| **Redis** | Celery task broker (db 1), result backend (db 2), caching (db 0) |
| **Stripe** | Payment processing, subscription management, customer portal |
| **AliExpress API** | Product search, data fetching (mock in development) |
| **CJ Dropshipping API** | Product search, data fetching (mock in development) |
| **Spocket API** | Product search, data fetching (mock in development) |

---

## Milestones and Progress

### Phase 1: Core Infrastructure (Complete)

- [x] FastAPI backend scaffolding with service template
- [x] Database models and schema isolation
- [x] JWT authentication and registration
- [x] Stripe billing integration (mock mode)
- [x] API key management
- [x] Health check endpoint
- [x] Usage reporting endpoint

### Phase 2: Core Features (Complete)

- [x] Import job CRUD and lifecycle management
- [x] Bulk import (up to 50 URLs)
- [x] Import cancellation and retry
- [x] Plan-based import limit enforcement
- [x] Supplier account management (CRUD)
- [x] Store connection management with default handling
- [x] Product search (mock data)
- [x] Product preview with caching (24h TTL)

### Phase 3: Monitoring and Integration (Complete)

- [x] Price watch CRUD and sync
- [x] Manual price sync trigger
- [x] TrendScout product-scored webhook (auto-import >= 50)
- [x] Cross-service user provisioning
- [x] Import history audit trail
- [x] Next.js dashboard with all pages

### Phase 4: Production Readiness (Pending)

- [ ] Real supplier API integrations (AliExpress, CJ, Spocket)
- [ ] Celery task implementation for import processing
- [ ] Celery beat schedule for periodic price sync
- [ ] Credential encryption for supplier accounts
- [ ] Email notifications for price changes
- [ ] Rate limiting and abuse prevention
- [ ] Production deployment and monitoring

---

## Test Coverage

**Total**: 130 backend tests across 11 test files.

| Area | Tests | Coverage |
|---|---|---|
| Auth | 12+ | Register, login, refresh, profile, provisioning, duplicate email, invalid credentials |
| Imports | 20+ | Create, list, get, cancel, retry, bulk, plan limits, invalid source, status filters |
| Products | 12+ | Search, preview, URL validation, source auto-detection, invalid URLs |
| Suppliers | 12+ | CRUD, duplicate name+platform, partial updates |
| Connections | 15+ | CRUD, default auto-set, default promotion, set-default, duplicate URL |
| Price Watch | 12+ | CRUD, sync, connection_id filtering, threshold |
| Billing | 10+ | Plans listing, checkout (mock), portal, overview, usage |
| Webhooks | 8+ | Stripe events, product-scored above/below threshold |
| API Keys | 8+ | Create, list, revoke, key authentication |
| Health | 2+ | Health check response |

Tests use schema-based isolation (`sourcepilot_test` PostgreSQL schema) with per-test table truncation.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Supplier API rate limits | Import delays, failed jobs | Implement exponential backoff, request queuing, per-user rate limits |
| Supplier API changes | Broken product search/import | Version-specific adapters, monitoring for API changes, fallback mock mode |
| Price sync volume | Database load, API cost | Batch processing, configurable sync intervals, prioritize recently-changed products |
| Stale product cache | Incorrect pricing/availability | 24h TTL on cache, manual refresh option, cache invalidation on import |
| Credential security | Supplier account compromise | Encrypt credentials at rest, audit access logs, rotate keys periodically |

---

## Key Metrics to Track

1. **Imports per day/week/month** -- Overall service adoption
2. **Import success rate** -- Percentage of completed vs failed imports
3. **Average import duration** -- Time from pending to completed
4. **Active price watches** -- Engagement with monitoring feature
5. **Price change detection rate** -- How often price changes are found
6. **Plan conversion rate** -- Free to Pro/Enterprise upgrades
7. **API key usage** -- Integration adoption
8. **Connected stores per user** -- Multi-store usage patterns

---

## Technical Notes for Stakeholder Communication

- The backend runs on **port 8109** and the dashboard on **port 3109**.
- **Mock mode** is active by default for development -- Stripe billing and supplier APIs return simulated data.
- The service uses **Celery** for background job processing (import execution, price sync). Jobs are queued and processed asynchronously.
- **Schema isolation** ensures SourcePilot's database tables don't conflict with other services sharing the same PostgreSQL instance.
- The **TrendScout integration** allows automatic product imports when TrendScout identifies high-scoring products (score >= 50/100).
