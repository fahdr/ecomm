# Project Manager Guide

**For Project Managers:** AdScale is Feature A7 in the dropshipping platform's Phase 2 (Automation & AI). It is an AI Ad Campaign Manager that enables users to manage paid advertising across Google Ads and Meta (Facebook + Instagram) from a single dashboard. The service is fully scaffolded with a working backend, dashboard, and landing page, backed by 164 automated tests.

---

## Overview

AdScale lets dropshipping store owners launch, manage, and optimize advertising campaigns without switching between Google Ads and Meta Ads Manager. It provides AI-generated ad copy, automated rules for campaign management (pause underperformers, scale winners), and centralized performance analytics with ROAS tracking.

### Key Differentiators

| Differentiator | Description |
|----------------|-------------|
| **Dual-Platform Support** | Manage Google Ads and Meta Ads from one unified interface instead of two separate ad managers |
| **AI Ad Copy Generation** | Claude-powered headline, description, and CTA generation from product descriptions -- saves hours of copywriting per campaign |
| **Auto-Optimization Rules** | Set-and-forget rules that automatically pause low-ROAS campaigns, scale high-performers, or adjust budgets based on real performance |
| **ROAS-First Analytics** | Performance dashboard built around Return on Ad Spend -- the metric that matters most to e-commerce advertisers |
| **Platform Integration** | Seamlessly connects with the dropshipping platform for product data import and cross-service billing |

---

## Architecture

AdScale follows a three-tier architecture that mirrors all services in the platform:

```
                    +------------------+
                    |   Landing Page   |  (port 3207)
                    |   Next.js 16     |  Static marketing site
                    +--------+---------+
                             |
                    +--------v---------+
                    |    Dashboard     |  (port 3107)
                    |    Next.js 16    |  App Router + Tailwind
                    +--------+---------+
                             |
                    +--------v---------+
                    |   Backend API    |  (port 8107)
                    |   FastAPI        |  REST API + JWT Auth
                    +--------+---------+
                             |
               +-------------+-------------+
               |                           |
      +--------v---------+       +--------v---------+
      |   PostgreSQL 16  |       |     Redis 7      |
      |   (port 5507)    |       |   (port 6407)    |
      +------------------+       +------------------+
```

---

## Current Status

| Metric | Value |
|--------|-------|
| Backend Tests | **164 passing** |
| Test Files | 8 (auth, accounts, campaigns, creatives, rules, billing, api-keys, health) |
| API Endpoints | 35+ across 9 route modules |
| Database Tables | 10 (users, subscriptions, api_keys, ad_accounts, campaigns, ad_groups, ad_creatives, campaign_metrics, optimization_rules + Alembic version) |
| Dashboard Pages | 9 (home, campaigns, creatives, analytics, billing, api-keys, settings, login, register) |
| Landing Pages | 2 (homepage, pricing) |
| Service Layer Files | 7 (auth, account, campaign, creative, metrics, optimization, billing) |
| Model Files | 10 (user, subscription, api_key, ad_account, campaign, ad_group, ad_creative, campaign_metrics, optimization_rule, base) |

### Feature Completion

| Feature Area | Status | Notes |
|-------------|--------|-------|
| User Auth (register, login, JWT, API keys) | Complete | 11 tests passing |
| Ad Account Connection (Google, Meta) | Complete | 15 tests, duplicate detection, soft disconnect |
| Campaign CRUD + Plan Limits | Complete | 20 tests, all objectives, cascade delete |
| Ad Group CRUD + Plan Limits | Complete | Tested via integration in creative tests |
| Creative CRUD + AI Copy | Complete | 16 tests, chain ownership validation, mock AI |
| Performance Metrics (ROAS, CPA, CTR) | Complete | Overview, per-campaign, date-range endpoints |
| Optimization Rules + Execute-Now | Complete | 20+ tests, 4 rule types, threshold evaluation |
| Billing (Stripe integration) | Complete | 9 tests, mock mode, 3 tiers |
| API Key Management | Complete | 5 tests, SHA-256 hashing, revocation |
| Dashboard UI | Complete | 9 pages, config-driven branding |
| Landing Page | Complete | 2 pages, hero, features, pricing cards |

---

## Pricing Model

| Tier | Monthly Price | Campaigns | Ad Groups | Platforms | AI Copy | Auto-Optimize | API Access | Trial |
|------|-------------|-----------|-----------|-----------|---------|---------------|------------|-------|
| **Free** | $0 | 2 | 5 | 1 | 5/month | No | No | -- |
| **Pro** | $49 | 25 | 100 | Google + Meta | Unlimited | Yes + ROAS tracking | Yes | 14 days |
| **Enterprise** | $149 | Unlimited | Unlimited | All + API | Priority AI | Yes + ROAS targets + Dedicated support | Yes | 14 days |

### Revenue Considerations

- Free tier drives user acquisition (2 campaigns is enough to test the product)
- Pro tier ($49/mo) is the primary revenue driver -- targets active advertisers managing 3-25 campaigns
- Enterprise tier ($149/mo) targets agencies and power users managing large campaign portfolios
- Plan limits are enforced at the API layer (campaigns return `403` when limit is reached)

---

## Integration Points

### With the Dropshipping Platform

| Integration | Direction | Mechanism | Purpose |
|-------------|-----------|-----------|---------|
| User Provisioning | Platform -> AdScale | `POST /auth/provision` with API key | Auto-create AdScale user when store owner activates the service |
| Usage Reporting | AdScale -> Platform | `GET /usage` with API key | Sync billing metrics to the platform's unified billing dashboard |
| Stripe Webhooks | Stripe -> AdScale | `POST /webhooks/stripe` | Process subscription creation, updates, and cancellations |
| Product Data | Platform -> AdScale | Future: product catalog sync | Auto-generate campaigns from store products |

### External Services

| Service | Purpose | Status |
|---------|---------|--------|
| Google Ads API | Campaign delivery and metrics sync | Mock (ready for production integration) |
| Meta Marketing API | Campaign delivery and metrics sync | Mock (ready for production integration) |
| Stripe | Subscription billing | Integrated (mock mode for dev) |
| Claude AI (Anthropic) | Ad copy generation | Mock (deterministic responses in dev) |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Google/Meta API rate limits | Medium | High | Implement request queuing via Celery + exponential backoff |
| Ad platform policy changes | Medium | Medium | Abstract platform-specific logic into adapter pattern |
| AI copy quality inconsistency | Low | Medium | Human review option + A/B testing framework |
| Stripe webhook delivery failures | Low | High | Idempotent webhook handler + manual reconciliation endpoint |
| Free tier abuse (many accounts) | Medium | Low | Rate limiting per IP + email verification |
| Campaign metrics sync delays | Medium | Medium | Celery beat scheduling with retry logic + "last synced" indicator in UI |

---

## Key Metrics to Track (Post-Launch)

| Metric | Definition | Target |
|--------|-----------|--------|
| Activation Rate | % of sign-ups who connect an ad account | > 40% |
| Campaign Creation Rate | % of users who create at least 1 campaign | > 60% |
| Free-to-Pro Conversion | % of free users who upgrade to Pro | > 8% |
| Pro-to-Enterprise Conversion | % of Pro users who upgrade to Enterprise | > 5% |
| Monthly Churn | % of paid subscribers who cancel | < 5% |
| AI Copy Usage | Average AI copy generations per user per month | > 10 |
| Rule Execution Success | % of optimization rule executions without errors | > 99% |
| API Uptime | Service availability | > 99.9% |

---

## Team and Dependencies

### Development Dependencies

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery
- Frontend: Node 20, Next.js 16, Tailwind CSS, lucide-react icons
- Infrastructure: PostgreSQL 16, Redis 7, Docker (devcontainer)

### External Dependencies

- Stripe account for billing (mock mode available for dev)
- Google Ads API credentials (future: for production campaign delivery)
- Meta Marketing API credentials (future: for production campaign delivery)
- Anthropic API key (future: for production AI copy generation)

---

## Timeline Considerations

The service is fully scaffolded and functionally complete for demo purposes. The following items are needed for production readiness:

1. **Google Ads API Integration** -- Replace mock OAuth flow and campaign sync with real API calls
2. **Meta Marketing API Integration** -- Same as above for Facebook/Instagram
3. **Claude AI Production Integration** -- Replace mock copy generation with real Anthropic API calls
4. **Celery Beat Scheduling** -- Set up periodic tasks for metrics sync and rule evaluation
5. **Email Verification** -- Add email confirmation for new registrations
6. **Rate Limiting** -- Add API rate limits per tier
7. **Monitoring & Alerting** -- Set up health checks, error tracking, and performance monitoring
