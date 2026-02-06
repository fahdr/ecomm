# Project Manager Guide

## Project Overview

The Dropshipping Platform is a SaaS product that allows entrepreneurs to create, manage, and automate online dropshipping stores. The platform handles store creation, product sourcing (with AI-powered research), checkout via Stripe, and marketing automation — all from a single dashboard.

### Key Differentiators

- **AI-powered product research** — automated daily trend analysis from multiple sources
- **One-click product import** — AI generates titles, descriptions, and SEO metadata
- **Multi-tenant storefront** — each store gets its own subdomain (e.g., `mystore.platform.com`)
- **Subscription billing** — three tiers (Starter / Growth / Pro)

## Architecture Summary

The platform has three main applications:

| Application | Purpose | Users |
|-------------|---------|-------|
| **Backend API** | Handles all business logic, data, and integrations | Internal (consumed by frontends) |
| **Dashboard** | Web app for store owners to manage their business | Store owners / admins |
| **Storefront** | Customer-facing online store | Shoppers / end customers |

Supporting infrastructure:
- **PostgreSQL** — stores all data (users, stores, products, orders)
- **Redis** — caching and background job messaging
- **Celery** — runs scheduled and async tasks (product research, email, imports)

## Current Status

**Feature 1: Project Scaffolding** — Complete

All three applications are scaffolded and runnable in the local development environment. The backend serves a health check endpoint, the database is connected, and the task queue is wired up. One automated test passes.

**Next up: Feature 2 (User Authentication)**

## Feature Roadmap

| # | Feature | Priority | Effort | Status | Dependencies |
|---|---------|----------|--------|--------|-------------|
| 1 | Project Scaffolding & Local Dev | Must have | Small | **Done** | — |
| 2 | User Authentication | Must have | Medium | Not started | Feature 1 |
| 3 | Store Creation | Must have | Medium | Not started | Feature 2 |
| 4 | Storefront (Public-Facing) | Must have | Medium | Not started | Feature 3 |
| 5 | Product Management (CRUD) | Must have | Medium | Not started | Feature 3 |
| 6 | Shopping Cart & Checkout | Must have | Medium | Not started | Features 4, 5 |
| 7 | Stripe Subscriptions (SaaS Billing) | Must have | Medium | Not started | Feature 2 |
| 8 | Product Research Automation | High | Large | Not started | Features 3, 5 |
| 9 | Automated Product Import + AI Content | High | Medium | Not started | Features 5, 8 |
| 10 | SEO Automation | Medium | Medium | Not started | Features 4, 5 |
| 11 | Email Automation | Medium | Medium | Not started | Feature 6 |
| 12 | Analytics Dashboard | Medium | Medium | Not started | Feature 6 |
| 13 | Kubernetes Deployment & CI/CD | Must have | Medium | Not started | All features |

### Feature Dependency Chain

```
Feature 1 (Scaffolding)
  └── Feature 2 (Auth)
        ├── Feature 3 (Stores)
        │     ├── Feature 4 (Storefront)
        │     │     └── Feature 10 (SEO)
        │     ├── Feature 5 (Products)
        │     │     ├── Feature 6 (Cart & Checkout)
        │     │     │     ├── Feature 11 (Email)
        │     │     │     └── Feature 12 (Analytics)
        │     │     ├── Feature 8 (Product Research)
        │     │     │     └── Feature 9 (AI Import)
        │     │     └── Feature 10 (SEO)
        │     └── Feature 8 (Product Research)
        └── Feature 7 (Subscriptions)
  Feature 13 (Deployment) — after all features
```

## Working Agreement

These principles are documented in the backlog and guide all development:

1. **One feature at a time.** Finish and test locally before starting the next.
2. **Tests are mandatory** for backend API endpoints.
3. **No premature optimization.** Get it working, then improve.
4. **Backend first, then frontend.** The API is the source of truth.
5. **Local dev only** until Feature 13 (Kubernetes deployment).

## Tech Stack Overview

| Component | What it does |
|-----------|-------------|
| **FastAPI** (Python) | Handles HTTP requests, validates data, runs business logic |
| **PostgreSQL** | Stores all persistent data (users, stores, products, orders) |
| **Redis** | Fast in-memory store for caching and message passing |
| **Celery** | Runs background tasks (product research, emails, imports) |
| **Next.js** (TypeScript) | Renders the dashboard and storefront web pages |
| **Tailwind CSS** | Styling framework for consistent, responsive UI |
| **Shadcn/ui** | Pre-built accessible UI components for the dashboard |
| **Stripe** | Handles payments (store checkout + platform subscriptions) |
| **Claude API** | AI for product analysis, content generation, SEO |
| **Alembic** | Manages database schema changes safely |
| **Kubernetes** | Production hosting and scaling (Feature 13) |

## Key Documents

| Document | Location | Contents |
|----------|----------|----------|
| Architecture | `plan/ARCHITECTURE.md` | Tech decisions, data model, API conventions |
| Feature Backlog | `plan/BACKLOG.md` | All 13 features with acceptance criteria and tasks |
| Master Plan | `dropshipping-platform-master-plan.md` | Vision, business model, cost analysis, scaling roadmap |
| Developer Guide | `docs/DEVELOPER.md` | Setup instructions, code structure, conventions |
| QA Guide | `docs/QA_ENGINEER.md` | Testing strategy, tools, and procedures |
