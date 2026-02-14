# Project Manager Guide — Dropshipping Platform

**For Project Managers:**
This guide provides a high-level overview of the project's scope, current status, feature roadmap, and key metrics for tracking progress.

## Project Overview

The Dropshipping Platform is a SaaS product that allows entrepreneurs to create, manage, and automate online dropshipping stores. The platform handles store creation, product management, order processing, checkout via Stripe, theme customization, analytics, and customer account management — all from a single dashboard.

In Phase 3 the platform gained **ServiceBridge** — an event-driven integration layer that automatically dispatches webhooks to 8 standalone AI-powered SaaS services (TrendScout, ContentForge, RankPilot, FlowSend, SpyDrop, PostPilot, AdScale, ShopChat) whenever products, orders, or customers change, enabling end-to-end automation across the entire suite.

### Key Differentiators

- **Block-based theme engine** — 13 configurable block types, 11 preset themes, full color/typography/layout customization
- **Multi-tenant storefronts** — each store gets its own themed web experience with customer accounts
- **Full order lifecycle** — pending -> paid -> shipped -> delivered with tracking numbers
- **Customer accounts** — registration, addresses, wishlists, order history
- **Subscription billing** — three tiers (Starter / Growth / Pro) via Stripe
- **Animation system** — Motion-powered animations throughout storefront and dashboard
- **Export & operations** — CSV export, inventory alerts, internal order notes
- **ServiceBridge** — automatic event-driven integration with 8 AI services (trend research, content generation, SEO, email, competitor monitoring, social media, ads, and chat)

## Architecture Summary

The platform has three main applications:

| Application | Purpose | Users | Pages |
|-------------|---------|-------|-------|
| **Backend API** | Handles all business logic, data, and integrations | Internal (consumed by frontends) | 100+ endpoints |
| **Dashboard** | Web app for store owners to manage their business | Store owners / admins | 34 pages |
| **Storefront** | Customer-facing online store | Shoppers / end customers | 18 pages |

Supporting infrastructure:
- **PostgreSQL 16** — stores all data (~37 tables across 22 models)
- **Redis 7** — caching and background job messaging
- **Celery** — runs scheduled and async tasks (21 task functions)
- **ServiceBridge** — HMAC-signed webhook dispatcher connecting to 8 SaaS services
- **8 SaaS Services** — TrendScout, ContentForge, RankPilot, FlowSend, SpyDrop, PostPilot, AdScale, ShopChat (each with its own backend, dashboard, and landing page)
- **LLM Gateway** — centralized AI provider routing (port 8200)
- **Shared Packages** — `ecomm_core` (auth, billing, DB, models) and `ecomm_connectors` (Shopify, WooCommerce)

## Current Status

### Completed Work

| Phase | Scope | Status |
|-------|-------|--------|
| **Features 1-7.5** | Core platform (auth, stores, products, orders, checkout, subscriptions) | **Complete** |
| **Phase 1 (F8-F30)** | All 23 features: categories, reviews, analytics, discounts, gift cards, themes, customer accounts, refunds, tax, currency, domains, teams, webhooks, A/B tests, segments, suppliers, bulk ops, fraud, email, search, notifications, upsells, export | **Complete** |
| **Polish Plan (A-G)** | UI overhaul, sidebar, top bar, fulfillment flow, order enhancements, store improvements, seed data | **Complete** |
| **Phase 2 Polish** | Theme Engine v2, Animation & Motion, Storefront Visual, Dashboard Enhancements, Data & QoL | **Complete** |
| **Phase 3 ServiceBridge** | Event-driven integration with 8 SaaS services, HMAC-signed webhooks, dashboard activity page, per-product/order service status panels, services hub | **Complete** |

### Key Metrics

| Metric | Count |
|--------|-------|
| Backend tests passing | 580 |
| E2E tests passing | 200+ |
| Backend test files | ~35 |
| E2E spec files | 25 |
| Dashboard pages | 34 |
| Storefront pages | 18 |
| API routers | 36 |
| Database models | 22 |
| Database tables | ~37 |
| Service files | 30 |
| Alembic migrations | 13 |
| Preset themes | 11 |
| Block types | 13 |
| Heading font options | 12 |
| Body font options | 8 |
| ServiceBridge event types | 5 |
| Connected service slots | 8 |
| Celery task functions | 21 |

## Feature Scope

### Core Platform (Phase 1)

- User registration and JWT authentication
- Multi-store management with settings
- Product CRUD with variants, images, inventory
- Order processing with Stripe checkout
- Supplier management and auto-fulfillment
- 30+ features including discounts, categories, reviews, analytics, themes, etc.

### ServiceBridge (Phase 3)

- Automatic event dispatch when products/orders/customers change
- HMAC-signed webhooks to 8 connected SaaS services
- Dashboard activity page with KPIs, filters, pagination
- Per-product and per-order service status panels
- Services hub with health indicators

## Milestones

| Milestone | Status | Tests |
|-----------|--------|-------|
| Core platform (30 features) | Complete | 541 |
| ServiceBridge backend | Complete | 39 |
| ServiceBridge dashboard UI | Complete | -- |
| ServiceBridge e2e tests | Complete | 15 |
| **Total** | **Complete** | **580 + 15 e2e** |

## Dependencies

- **8 SaaS services**: Each must have `POST /api/v1/webhooks/platform-events` receiver
- **Shared packages**: `ecomm_core` provides auth, billing, DB across all services
- **LLM Gateway**: Centralized AI provider routing (port 8200)
- **PostgreSQL**: Shared database with schema-based isolation per service

## Feature Roadmap — Complete History

### Phase 1: Core Platform (Features 1-7)

| # | Feature | Status |
|---|---------|--------|
| 1 | Project Scaffolding & Local Dev | **Done** |
| 2 | User Authentication | **Done** |
| 3 | Store Creation | **Done** |
| 4 | Storefront (Public-Facing) | **Done** |
| 5 | Product Management (CRUD) | **Done** |
| 6 | Shopping Cart & Checkout | **Done** |
| 7 | Stripe Subscriptions (SaaS Billing) | **Done** |

### Phase 1 Extended: Features 8-30

| # | Feature | Status |
|---|---------|--------|
| 8 | Categories | **Done** |
| 9 | Reviews & Ratings | **Done** |
| 10 | Analytics | **Done** |
| 11 | Discounts & Coupons | **Done** |
| 12 | Gift Cards | **Done** |
| 13 | Theme System | **Done** |
| 14 | Customer Accounts | **Done** |
| 15 | Store Themes (Full) | **Done** |
| 16 | Refunds | **Done** |
| 17 | Tax Configuration | **Done** |
| 18 | Currency Settings | **Done** |
| 19 | Custom Domains | **Done** |
| 20 | Team Management | **Done** |
| 21 | Webhooks | **Done** |
| 22 | A/B Tests | **Done** |
| 23 | Customer Segments | **Done** |
| 24 | Supplier Management | **Done** |
| 25 | Bulk Operations | **Done** |
| 26 | Fraud Detection | **Done** |
| 27 | Email Templates | **Done** |
| 28 | Search | **Done** |
| 29 | Notifications | **Done** |
| 30 | Upsells | **Done** |

### Polish Plan (A-G)

| Phase | Scope | Status |
|-------|-------|--------|
| A | Order enhancements (fulfillment, tracking, shipping addresses) | **Done** |
| B | Customer accounts (auth, addresses, wishlist, order history) | **Done** |
| C | Storefront improvements (policies, search autocomplete, mobile menu) | **Done** |
| D | Dashboard UI overhaul (sidebar, top bar, shell, authenticated layout) | **Done** |
| E | Store improvements (store context, breadcrumbs) | **Done** |
| F | Seed data (Volt Electronics demo store) | **Done** |
| G | E2E test coverage expansion | **Done** |

### Phase 2 Polish (Phases 1-5)

| Phase | Scope | Status |
|-------|-------|--------|
| 2.1 | Theme Engine v2 — 5 new blocks, hero product showcase, block config editor, 4 new presets | **Done** |
| 2.2 | Animation & Motion — motion primitives, staggered grids, micro-interactions, skeletons | **Done** |
| 2.3 | Storefront Visual — product badges, recently viewed, enhanced product cards | **Done** |
| 2.4 | Dashboard Enhancements — KPI dashboards, command palette, notification badges, analytics | **Done** |
| 2.5 | Data & QoL — CSV export, order notes, inventory alerts, seed script updates | **Done** |

## Tech Stack Overview

| Component | What it does |
|-----------|-------------|
| **FastAPI** (Python 3.12) | Handles HTTP requests, validates data, runs business logic |
| **PostgreSQL 16** | Stores all persistent data (~37 tables) |
| **Redis 7** | Fast in-memory store for caching and message passing |
| **Celery** | Runs background tasks (21 task functions including ServiceBridge dispatch) |
| **Next.js 16** (TypeScript) | Renders the dashboard and storefront web pages |
| **Tailwind CSS 4** | Styling framework for consistent, responsive UI |
| **Shadcn/ui** | Pre-built accessible UI components for the dashboard |
| **Motion** (framer-motion) | Animation library for storefront and dashboard |
| **Recharts** | Chart library for analytics visualizations |
| **Stripe** | Handles payments (store checkout + platform subscriptions) |
| **Playwright** | E2E browser testing framework |
| **Alembic** | Manages database schema changes safely |

## Working Agreement

These principles guide all development:

1. **One feature at a time.** Finish and test locally before starting the next.
2. **Tests are mandatory** for backend API endpoints and critical UI flows.
3. **No premature optimization.** Get it working, then improve.
4. **Backend first, then frontend.** The API is the source of truth.
5. **Local dev only** until deployment infrastructure is built.
6. **Gitflow branching.** Feature branches off `main`, squash-merge via PRs.

## Demo Environment

A seed script populates the database with a fully configured demo store for stakeholder demos, QA testing, and development.

**To run:** `npx tsx scripts/seed.ts` (requires backend running on port 8000)

**Demo credentials:**

| Role | Email | Password |
|------|-------|----------|
| Store Owner | `demo@example.com` | `password123` |
| Customer (Alice) | `alice@example.com` | `password123` |
| Customer (Bob) | `bob@example.com` | `password123` |
| Customer (Carol) | `carol@example.com` | `password123` |

**Demo URLs:**
- Dashboard: `http://localhost:3000`
- Storefront: `http://localhost:3001?store=volt-electronics`
- API Docs: `http://localhost:8000/docs`

**Demo store contents:** 12 products (with images, variants, reviews), 4 orders across the full lifecycle, Cyberpunk theme with 8 custom blocks, 5 discount codes, 3 customer accounts with addresses/wishlists, and all platform features configured.

## Key Documents

| Document | Location | Contents |
|----------|----------|----------|
| Architecture | `plan/ARCHITECTURE.md` | Tech decisions, data model, API conventions |
| Feature Backlog | `plan/BACKLOG.md` | All features with acceptance criteria and tasks |
| Polish Plan | `plan/POLISH_PLAN.md` | Phase 2 Polish implementation details (Phases 1-5) |
| Developer Guide | `dropshipping/docs/DEVELOPER.md` | Setup instructions, code structure, conventions |
| QA Guide | `dropshipping/docs/QA_ENGINEER.md` | Testing strategy, tools, procedures, coverage |
| End User Guide | `dropshipping/docs/END_USER.md` | User-facing feature documentation |
| Implementation Steps | `dropshipping/docs/IMPLEMENTATION_STEPS.md` | Step-by-step implementation details per feature |
| ServiceBridge Developer | `dropshipping/docs/DEVELOPER.md` | ServiceBridge architecture, endpoints, event flow |
| ServiceBridge QA | `dropshipping/docs/QA_ENGINEER.md` | ServiceBridge test plans and acceptance criteria |

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Phase 3 standalone service complexity (8 services) | High | Each service is independently deployable with own backend, dashboard, and test suite; shared packages reduce duplication; ServiceBridge uses HMAC-signed webhooks for secure cross-service communication |
| AI API costs (Claude, OpenAI) | Medium | Mock mode for local dev; token usage monitoring; centralized routing via LLM Gateway |
| Stripe integration in production | Medium | Mock mode for local dev; webhook signature verification |
| Multi-tenant data isolation | High | All queries scoped by `store_id` + `user_id`; tested with cross-user isolation tests; schema-based test isolation per service |
| Test flakiness in CI | Low | Known flaky tests documented; retry mechanisms in place |
