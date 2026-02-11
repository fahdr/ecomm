# Project Manager Guide

**For Project Managers:**
This guide provides a high-level overview of the project's scope, current status, feature roadmap, and key metrics for tracking progress.

## Project Overview

The Dropshipping Platform is a SaaS product that allows entrepreneurs to create, manage, and automate online dropshipping stores. The platform handles store creation, product management, order processing, checkout via Stripe, theme customization, analytics, and customer account management — all from a single dashboard.

### Key Differentiators

- **Block-based theme engine** — 13 configurable block types, 11 preset themes, full color/typography/layout customization
- **Multi-tenant storefronts** — each store gets its own themed web experience with customer accounts
- **Full order lifecycle** — pending → paid → shipped → delivered with tracking numbers
- **Customer accounts** — registration, addresses, wishlists, order history
- **Subscription billing** — three tiers (Starter / Growth / Pro) via Stripe
- **Animation system** — Motion-powered animations throughout storefront and dashboard
- **Export & operations** — CSV export, inventory alerts, internal order notes

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
- **Celery** — runs scheduled and async tasks

## Current Status

### Completed Work

| Phase | Scope | Status |
|-------|-------|--------|
| **Features 1-7.5** | Core platform (auth, stores, products, orders, checkout, subscriptions) | **Complete** |
| **Phase 1 (F8-F30)** | All 23 features: categories, reviews, analytics, discounts, gift cards, themes, customer accounts, refunds, tax, currency, domains, teams, webhooks, A/B tests, segments, suppliers, bulk ops, fraud, email, search, notifications, upsells, export | **Complete** |
| **Polish Plan (A-G)** | UI overhaul, sidebar, top bar, fulfillment flow, order enhancements, store improvements, seed data | **Complete** |
| **Phase 2 Polish** | Theme Engine v2, Animation & Motion, Storefront Visual, Dashboard Enhancements, Data & QoL | **Complete** |

### Key Metrics

| Metric | Count |
|--------|-------|
| Backend tests passing | 329+ |
| E2E tests passing | 187+ |
| Backend test files | 29 |
| E2E spec files | 24 |
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

### What's Next

**Phase 2: Automation & AI** — The next major phase adds AI-powered automation:

| Feature | Description |
|---------|-------------|
| A1: Product Research | Automated daily trend analysis from multiple sources |
| A2: AI Import | One-click product import with AI-generated content |
| A3: SEO Automation | Auto-generated sitemaps, schema markup, AI blog posts |
| A4: Email Marketing | Welcome emails, abandoned cart, order confirmations |
| A5: Competitor Monitoring | Track competitor pricing and inventory |
| A6: Social Media | Automated social media content generation |
| A7: Ad Campaigns | AI-powered ad campaign management |
| A8: AI Chatbot | Customer-facing AI chat support |

These features will be built in a separate `automation/` service (standalone FastAPI + Celery) that communicates with the backend via HTTP API.

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
| **Celery** | Runs background tasks |
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
| Developer Guide | `docs/DEVELOPER.md` | Setup instructions, code structure, conventions |
| QA Guide | `docs/QA_ENGINEER.md` | Testing strategy, tools, procedures, coverage |
| End User Guide | `docs/END_USER.md` | User-facing feature documentation |
| Implementation Steps | `docs/IMPLEMENTATION_STEPS.md` | Step-by-step implementation details per feature |

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Automation service complexity (A1-A8) | High | Separate `automation/` service with own database; communicates via HTTP only |
| AI API costs (Claude, OpenAI) | Medium | Mock mode for local dev; token usage monitoring |
| Stripe integration in production | Medium | Mock mode for local dev; webhook signature verification |
| Multi-tenant data isolation | High | All queries scoped by `store_id` + `user_id`; tested with cross-user isolation tests |
| Test flakiness in CI | Low | Known flaky tests documented; retry mechanisms in place |
