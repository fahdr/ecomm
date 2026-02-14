# RankPilot Project Manager Guide

## Overview

RankPilot is an **Automated SEO Engine** -- a standalone SaaS product that helps e-commerce store owners improve their search engine rankings. It is designated as **Feature A3** in the platform roadmap and is the most feature-rich service in the ecosystem.

**Key value proposition**: Users add their website domain, and RankPilot automates the SEO optimization process -- generating blog content, tracking keyword rankings, running SEO health audits, and producing JSON-LD structured data for rich search results.

---

## Differentiators

RankPilot stands out among the platform's microservices in several ways:

1. **Most API Endpoints**: 5 domain-specific route files (`sites.py`, `blog_posts.py`, `keywords.py`, `audits.py`, `schema.py`) plus standard auth, billing, API keys, usage, and webhooks -- totaling 20+ unique endpoints.
2. **Dual Monetization Levers**: Plan limits enforce both a primary metric (blog posts/month via `max_items`) and a secondary metric (total keywords tracked via `max_secondary`), giving users two distinct reasons to upgrade.
3. **AI Content Generation**: Blog post generation via AI is the primary value driver that differentiates paid plans from the free tier.
4. **Cross-Service Integration**: Users can be provisioned from the dropshipping platform via the `/auth/provision` endpoint, and usage can be polled via the `/usage` endpoint for aggregated billing dashboards.
5. **Config-Driven Dashboard**: The entire frontend branding, navigation, and billing UI is driven by a single `service.config.ts` file, making rebranding trivial.

---

## Architecture

```
                    +-------------------+
                    |   Landing Page    |
                    |  (Next.js, :3203) |
                    +--------+----------+
                             |
                    +--------v----------+
                    |    Dashboard      |
                    |  (Next.js, :3103) |
                    +--------+----------+
                             |
                    +--------v----------+
                    |   Backend API     |
                    | (FastAPI, :8103)  |
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+        +----------v---------+
    |   PostgreSQL 16   |        |     Redis 7        |
    |     (:5503)       |        |    (:6403)         |
    +-------------------+        +----+---------------+
                                      |
                                +-----v--------+
                                |   Celery     |
                                | (Background) |
                                +--------------+
```

### Component Summary

| Component | Technology | Port | Status |
|-----------|-----------|------|--------|
| Backend API | FastAPI + SQLAlchemy 2.0 | 8103 | Complete |
| Dashboard | Next.js 16 + Tailwind | 3103 | Complete (9 pages) |
| Landing Page | Next.js 16 (static) | 3203 | Complete |
| Database | PostgreSQL 16 | 5503 | Complete (8 tables) |
| Cache/Queue | Redis 7 | 6403 | Complete |
| Task Queue | Celery | -- | Scaffolded |

---

## Current Status

| Area | Status | Detail |
|------|--------|--------|
| Backend API | Complete | 13 route files, 20+ endpoints, all CRUD + business logic |
| Database | Complete | 8 domain tables + standard auth/billing tables |
| Service Layer | Complete | 7 service modules with full business logic |
| Test Suite | Complete | **74 backend tests** across 8 test files |
| Dashboard | Complete | 9 pages: login, register, home, sites, keywords, audits, billing, API keys, settings |
| Landing Page | Complete | Static marketing page |
| Plan Enforcement | Complete | Blog post monthly limits + keyword total limits |
| Stripe Integration | Complete | Mock mode + production Stripe support |
| Cross-Service API | Complete | Provision endpoint + API key auth + usage reporting |

---

## Quality Metrics

| Metric | Value |
|--------|-------|
| Backend Tests | 74 |
| Test Files | 8 |
| API Route Files | 13 (5 domain-specific + 8 standard) |
| Service Modules | 7 |
| Database Models | 9 |
| Database Tables | 8+ |
| Dashboard Pages | 9 |
| API Endpoints | 20+ |

---

## Pricing Model

| Tier | Monthly Price | Blog Posts/Month | Keywords Tracked | Sites | Schema Markup | API Access | Trial |
|------|-------------|-----------------|-----------------|-------|---------------|------------|-------|
| **Free** | $0 | 2 | 20 | 1 | Basic | No | -- |
| **Pro** | $29 | 20 | 200 | 5 | Advanced JSON-LD + Content gap | Yes | 14 days |
| **Enterprise** | $99 | Unlimited | Unlimited | Unlimited | Full + Custom templates | Yes | 14 days |

### Revenue Drivers

1. **Blog Post Limits**: Free users hit the 2 posts/month cap quickly. AI-generated content quality encourages upgrading to create more.
2. **Keyword Limits**: SEO-serious users tracking many keywords need Pro (200) or Enterprise (unlimited).
3. **API Access**: Enterprise customers integrating RankPilot into their workflows require API key authentication (only available on Pro and Enterprise).

---

## Integration with Dropshipping Platform

RankPilot integrates with the main dropshipping platform through two mechanisms:

### User Provisioning

The platform can create RankPilot accounts for its users via:

```
POST /api/v1/auth/provision
```

This creates (or links) a user account with a specific plan tier and returns an API key for subsequent requests. The `external_platform_id` and `external_store_id` fields link the RankPilot user back to the platform.

### Usage Reporting

The platform can poll usage data via:

```
GET /api/v1/usage
```

This returns current billing period metrics (blog posts created, keywords tracked) that the platform can display on its aggregated billing dashboard. Supports API key authentication.

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| AI generation quality (currently mock) | High | Medium | Production integration with Anthropic Claude API; human review workflow |
| Keyword rank data accuracy (currently mock) | High | Medium | Integration with SerpAPI or DataForSEO for real rank data |
| SEO audit depth (currently mock) | Medium | Medium | Integration with real site crawlers (Screaming Frog API, custom crawler) |
| Domain verification security | Medium | Low | Production implementation of DNS TXT, meta tag, or file verification |
| Stripe webhook reliability | Medium | Low | Idempotent webhook handlers, retry logic, dead letter queue |
| Free tier abuse | Low | Medium | Rate limiting, CAPTCHA, email verification |
| Database performance at scale | Medium | Low | Indexing strategy in place (user_id, site_id, domain); connection pooling |

---

## Feature Roadmap (Future)

| Feature | Priority | Description |
|---------|----------|-------------|
| Real AI content generation | High | Replace mock with Anthropic Claude API integration |
| Real keyword rank tracking | High | Integrate SerpAPI/DataForSEO for actual SERP position data |
| Real SEO auditing | High | Build site crawler for on-page SEO analysis |
| Real domain verification | Medium | DNS TXT record, meta tag, or file upload verification |
| Competitor analysis | Medium | Track competitor keyword rankings for comparison |
| Content calendar | Low | Schedule blog post publishing dates |
| Backlink monitoring | Low | Track incoming backlinks and domain authority |
| Google Search Console integration | Medium | Import real search performance data |

---

## Key Stakeholder Contacts

| Role | Responsibility |
|------|---------------|
| Developer | Backend API, service logic, database models, tests, dashboard pages |
| QA Engineer | Test execution, bug reporting, verification checklist sign-off |
| End User | Domain registration, blog creation, keyword tracking, audit review |

---

## Glossary

| Term | Definition |
|------|-----------|
| **Site** | A registered domain (e.g., example.com) that the user wants to optimize for SEO |
| **Blog Post** | An SEO-optimized article targeting specific keywords, created manually or via AI |
| **Keyword Tracking** | Monitoring where a specific search term ranks in search engine results |
| **SEO Audit** | An automated assessment of a site's SEO health, producing a score (0-100) and issues |
| **Schema Markup** | JSON-LD structured data that helps search engines understand page content |
| **JSON-LD** | JavaScript Object Notation for Linked Data -- a format for structured data in HTML |
| **Rich Snippet** | Enhanced search result display (star ratings, prices, FAQs) enabled by schema markup |
| **Plan Limit** | Resource cap based on subscription tier (e.g., 2 blog posts/month on free tier) |
| **Provisioning** | Creating a user account from the platform via API (cross-service integration) |
| **max_items** | Plan limit for primary resource (blog posts per month) |
| **max_secondary** | Plan limit for secondary resource (total keywords tracked) |
