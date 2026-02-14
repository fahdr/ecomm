# Project Manager Guide

**For Project Managers:** ContentForge is Feature A2 in the dropshipping platform roadmap. It is an independently hostable SaaS product that generates SEO-optimized product content using AI. This guide provides an overview of the project scope, current status, architecture, pricing, and risk areas.

---

## Project Overview

ContentForge transforms raw product data (URLs, CSV imports, or manual input) into polished, SEO-ready product listings in seconds. It generates titles, descriptions, meta tags, keywords, and bullet points using Claude AI, and handles product image download, optimization, and format conversion.

The service can operate as a standalone SaaS product or be integrated into the dropshipping platform via the provisioning API.

---

## Key Differentiators

| Differentiator | Description |
|----------------|-------------|
| **AI Content Generation** | Claude AI produces high-quality, contextual product copy tailored by tone and style templates. Supports professional, casual, luxury, playful, and technical voices. |
| **Image Optimization** | Product images are automatically downloaded, resized, converted to WebP format, and compressed for optimal storefront performance via Pillow. |
| **Template System** | System templates cover common use cases (Professional, Casual, Luxury, SEO-Focused). Custom templates let users match their brand voice for consistent messaging. |
| **Bulk Generation** | Pro and Enterprise users can import CSV files or URL lists for batch content generation, processing multiple products in a single operation. |
| **Pricing Calculator** | Built-in markup calculation with psychological rounding strategies ($X.99, $X.95, whole dollars) to optimize conversion rates. |

---

## Architecture Summary

ContentForge is a microservice with three components:

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 (async) | 8102 |
| Dashboard | Next.js 16 (App Router) + Tailwind | 3102 |
| Landing Page | Next.js 16 (static export) | 3202 |
| Database | PostgreSQL 16 | 5502 |
| Cache/Queue | Redis 7 | 6402 |
| Task Queue | Celery (async job processing) | -- |

The backend uses 7 database tables: `users`, `api_keys`, `subscriptions`, `generation_jobs`, `generated_content`, `image_jobs`, and `templates`.

---

## Current Status

| Area | Status | Details |
|------|--------|---------|
| Backend API | Complete | All CRUD endpoints, auth, billing, webhooks |
| Authentication | Complete | JWT tokens, API key auth, cross-service provisioning |
| Content Generation | Complete | Single + bulk generation, plan limit enforcement |
| Template System | Complete | System templates (read-only) + custom templates (CRUD) |
| Image Processing | Complete (mock) | Mock mode operational; real Pillow pipeline ready for integration |
| Billing / Stripe | Complete (mock) | Plans, checkout, portal, webhooks in mock mode |
| Dashboard | Complete | 8 pages: home, generate, templates, images, billing, API keys, settings, login/register |
| Landing Page | Scaffolded | Static marketing page structure in place |
| Backend Tests | Complete | 45 passing tests across 7 test files |
| AI Integration | Mock | Currently generates realistic mock content; Claude API integration ready |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Backend unit tests | 45 |
| Test files | 7 |
| Dashboard pages | 8 |
| API endpoints | 26 |
| Database tables | 7 |
| Database models | 7 (User, ApiKey, Subscription, GenerationJob, GeneratedContent, ImageJob, Template) |
| Subscription tiers | 3 (Free, Pro, Enterprise) |

---

## Pricing

| Tier | Price/Month | Generations/Month | Words/Generation | AI Images/Month | Templates | Other |
|------|-------------|-------------------|-----------------|----------------|-----------|-------|
| **Free** | $0 | 10 | 500 | 5 | Basic (system only) | -- |
| **Pro** | $19 | 200 | 2,000 | 100 | All + Bulk import | 14-day trial, API access |
| **Enterprise** | $79 | Unlimited | Unlimited | Unlimited | All + API + White-label | 14-day trial, API access |

### Pricing Details (from `constants/plans.py`)

| Tier | `max_items` (gens/month) | `max_secondary` (images/month) | `price_monthly_cents` | `trial_days` | `api_access` |
|------|--------------------------|-------------------------------|----------------------|---------------|-------------|
| Free | 10 | 5 | 0 | 0 | No |
| Pro | 200 | 100 | 1900 | 14 | Yes |
| Enterprise | -1 (unlimited) | -1 (unlimited) | 7900 | 14 | Yes |

---

## Integration with Dropshipping Platform

ContentForge integrates with the main dropshipping platform through:

1. **User Provisioning**: `POST /api/v1/auth/provision` creates a ContentForge user linked to a platform user/store. The platform sends `external_platform_id` and `external_store_id` to establish the link.

2. **API Key Authentication**: After provisioning, the platform receives an API key for making requests on behalf of the user via the `X-API-Key` header.

3. **Usage Reporting**: `GET /api/v1/usage` returns current billing period metrics (generations used, images processed) for display on the platform's billing dashboard.

4. **Webhook Sync**: Stripe webhooks keep subscription state synchronized. Events handled: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`.

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **AI API cost overruns** | High (operating cost) | Medium | Plan limits cap usage per tier. Monitor monthly costs. Consider caching common generations. |
| **AI content quality** | High (user satisfaction) | Low | Template system controls tone/style. Users can edit generated content. System templates are curated. |
| **Stripe webhook failures** | Medium (billing state) | Low | Idempotent webhook handler. Mock mode for local dev. Webhook retry built into Stripe. |
| **Image processing latency** | Medium (UX) | Medium | Celery async processing. Mock mode for development. Future: CDN integration for processed images. |
| **Plan limit gaming** | Low (revenue) | Low | Server-side enforcement in `content_service.py`. Billing period counted from 1st of month UTC. |
| **Cross-service auth complexity** | Medium (integration) | Medium | Simple provisioning API with API key auth. JWT for direct users, API key for platform integration. |
| **Database schema changes** | Low (development) | Medium | Alembic migrations with version control. Cascading deletes configured. |

---

## Roadmap Alignment

ContentForge is **Feature A2 (AI Import)** in the Phase 2: Automation & AI roadmap. It sits alongside:

- **A1**: Product Research (market analysis, trending products)
- **A3**: SEO Automation (meta tags, structured data)
- **A4**: Email Marketing (campaign builder, templates)
- **A5**: Competitor Monitoring (price tracking, alerts)
- **A6**: Social Media (scheduling, auto-posting)
- **A7**: Ad Campaigns (Google/Meta ad management)
- **A8**: AI Chatbot (customer support automation)

Each service follows the same architectural pattern: independent FastAPI backend, Next.js dashboard, shared landing page template, own database and Redis instance, and Stripe billing integration.

---

## Dashboard Pages

| Page | Route | Purpose |
|------|-------|---------|
| Dashboard | `/` | Overview with key metrics and recent activity |
| Generate | `/generate` | Create new content generation jobs |
| Templates | `/templates` | Manage system and custom templates |
| Images | `/images` | View and manage processed product images |
| History | `/history` | Browse past generation jobs |
| API Keys | `/api-keys` | Create and manage API keys for integrations |
| Billing | `/billing` | View plans, manage subscription, usage metrics |
| Settings | `/settings` | User profile and preferences |
| Login | `/login` | Sign in to existing account |
| Register | `/register` | Create new account |
