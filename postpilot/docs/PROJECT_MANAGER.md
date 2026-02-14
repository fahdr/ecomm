# Project Manager Guide

**For Project Managers:** PostPilot is Feature A6 in the platform roadmap -- a standalone SaaS product for social media automation. It enables users to connect Instagram, Facebook, and TikTok accounts, create and schedule posts with AI-generated captions, manage a content queue from product data, and track engagement analytics. PostPilot can operate independently or integrate with the dropshipping platform.

---

## Overview

### What PostPilot Does

PostPilot automates the social media workflow for e-commerce businesses:

1. **Connect** social media accounts (Instagram, Facebook, TikTok) via OAuth
2. **Create** posts with captions, media, and hashtags
3. **Generate** AI-powered captions from product data
4. **Schedule** posts for optimal publishing times
5. **Track** engagement metrics (impressions, reach, likes, comments, shares, clicks)

### Key Differentiators

| Differentiator | Description |
|----------------|-------------|
| **Multi-platform OAuth** | Single dashboard to manage Instagram, Facebook, and TikTok accounts |
| **AI Caption Generation** | Automatically generates platform-specific captions and hashtags from product data |
| **Content Queue Pipeline** | Structured workflow: add product -> generate AI caption -> review -> approve -> schedule |
| **Calendar Scheduling** | Visual calendar view of scheduled content with date-range grouping |
| **Engagement Analytics** | Aggregated and per-post metrics with engagement rate calculations |
| **Platform Integration** | Can be provisioned from the dropshipping platform via API for seamless integration |

---

## Architecture

### System Components

| Component | Technology | Port | Purpose |
|-----------|-----------|------|---------|
| Backend API | FastAPI + SQLAlchemy 2.0 | 8106 | REST API for all business logic |
| Dashboard | Next.js 16 + Tailwind | 3106 | User-facing management interface |
| Landing Page | Next.js 16 (static) | 3206 | Marketing page with pricing |
| Database | PostgreSQL 16 | 5506 | Persistent data storage |
| Cache/Queue | Redis 7 | 6406 | Caching and Celery task broker |
| Task Queue | Celery | -- | Background task processing for scheduled posts |

### Data Flow

```
User -> Dashboard (3106)
         |
         v
      Backend API (8106) --> PostgreSQL (5506)
         |
         v
      Celery Worker --> Social Platform APIs (Instagram/Facebook/TikTok)
         |
         v
      Redis (6406) <-- Metrics fetching
```

---

## Current Status

### Build Status

| Metric | Value | Notes |
|--------|-------|-------|
| Backend tests | **157 passing** | 7 test files, async tests with full DB isolation |
| Dashboard pages | **9 pages** | Home, Queue, Accounts, Posts, Billing, API Keys, Settings, Login, Register |
| Landing page sections | **8 components** | Hero, Features, How It Works, Stats, Pricing, CTA, Navbar, Footer |
| API endpoints | **27 endpoints** | Auth (6), Accounts (3), Posts (7), Queue (8), Analytics (3), Billing (5), API Keys (3), System (2) |
| Database models | **7 models** | User, SocialAccount, Post, PostMetrics, ContentQueue, Subscription, ApiKey |
| Service functions | **18 functions** | Across 5 service modules |

### Feature Completion

| Feature | Status | Notes |
|---------|--------|-------|
| User Authentication | Complete | Register, login, refresh, JWT + API key auth |
| Social Account Management | Complete | Connect/disconnect for Instagram, Facebook, TikTok |
| Post CRUD | Complete | Create, read, update, delete with status tracking |
| Post Scheduling | Complete | Schedule for future publication, calendar view |
| AI Content Queue | Complete | Product-to-caption pipeline with approve/reject workflow |
| AI Caption Generation | Complete (Mock) | Template-based; ready for real LLM integration |
| Post Analytics | Complete | Aggregated overview + per-post metrics |
| Billing / Subscriptions | Complete | Stripe integration (mock mode), 3 plan tiers |
| API Key Management | Complete | Create, list, revoke; SHA-256 hashed storage |
| Dashboard UI | Complete | 9 pages with animations, responsive layout |
| Landing Page | Complete | Marketing page with hero, features, pricing |
| OAuth Integration | Scaffold (Mock) | Simulated OAuth; ready for real platform OAuth |

---

## Pricing Tiers

| Tier | Monthly Price | Posts/Month | Platforms | AI Captions | Scheduling | Trial |
|------|-------------|-------------|-----------|-------------|------------|-------|
| **Free** | $0 | 10 | 1 platform | 5/month | Manual only | -- |
| **Pro** | $29 | 200 | All 3 (Instagram, Facebook, TikTok) | Unlimited | Auto-schedule with optimal timing | 14 days |
| **Enterprise** | $99 | Unlimited | All + API access | Unlimited + hashtags | Auto + analytics dashboard | 14 days |

### Plan Enforcement

Plan limits are enforced at the API layer:
- **Posts per month** (`max_items`): Checked when creating a new post. Returns 403 when limit reached.
- **Social accounts** (`max_secondary`): Checked when connecting a new account. Returns 403 when limit reached.
- **API access**: Only Pro and Enterprise tiers can use API keys for programmatic access.

---

## Integration with Dropshipping Platform

PostPilot integrates with the core dropshipping platform through:

1. **User Provisioning** (`POST /api/v1/auth/provision`): The platform creates PostPilot user accounts automatically when a store owner enables social media features. This endpoint accepts an API key and returns a PostPilot API key for subsequent requests.

2. **External IDs**: Users provisioned from the platform have `external_platform_id` and `external_store_id` fields set, linking them back to their platform account and store.

3. **Product Data**: The content queue accepts product data (title, description, price, images) that can be fed from the store's product catalog.

---

## Key Metrics to Track

### Product Metrics

| Metric | Current Value | Target |
|--------|---------------|--------|
| Backend test count | 157 | Maintain 100% coverage on critical paths |
| Dashboard pages | 9 | Add Calendar and Analytics pages |
| API response time | < 100ms (mock) | < 200ms with real platform APIs |
| Test reliability | Fully isolated | No flaky tests |

### Business Metrics (post-launch)

| Metric | Description |
|--------|-------------|
| User registrations | New accounts per week |
| Connected accounts | Total social accounts linked |
| Posts created | Monthly post volume |
| AI captions generated | Captions generated per user |
| Conversion to Pro | Free -> Pro upgrade rate |
| Churn rate | Monthly subscription cancellations |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **OAuth token expiry** | Users cannot post when tokens expire | High | Implement refresh token rotation + re-auth flow |
| **Platform API rate limits** | Posts fail to publish at scale | Medium | Queue system with retry logic + exponential backoff |
| **AI caption quality** | Users reject most AI-generated content | Medium | Allow tone selection, provide edit-before-approve workflow |
| **Stripe webhook reliability** | Subscription state gets out of sync | Low | Idempotent webhook handlers + periodic sync job |
| **Multi-platform formatting** | Captions look wrong on specific platforms | Medium | Platform-specific preview + character limit enforcement |
| **Data isolation breach** | User A accesses user B's data | Critical | All queries filter by user_id; comprehensive isolation tests |

---

## Roadmap (Post-Scaffold)

### Phase 1: Real Integrations

| Item | Description | Priority |
|------|-------------|----------|
| Real OAuth flows | Instagram Graph API, Facebook Pages API, TikTok Content Posting API | P0 |
| Real AI captions | Claude API integration for intelligent caption generation | P0 |
| Image upload | Media file upload + CDN storage (S3/R2) | P1 |
| Post publishing | Celery task to publish posts via platform APIs at scheduled time | P0 |
| Metrics fetching | Periodic Celery task to fetch engagement metrics from platforms | P1 |

### Phase 2: Advanced Features

| Item | Description | Priority |
|------|-------------|----------|
| Calendar page | Full calendar dashboard page with drag-and-drop scheduling | P1 |
| Analytics page | Rich analytics dashboard with charts and comparisons | P1 |
| Templates | Reusable post templates for common content types | P2 |
| Bulk operations | Bulk approve, schedule, or delete queue items | P2 |
| A/B testing | Publish caption variants and track which performs better | P3 |

### Phase 3: Growth

| Item | Description | Priority |
|------|-------------|----------|
| E2E tests | Playwright tests for dashboard flows | P1 |
| Onboarding wizard | Guided setup for new users | P2 |
| Team collaboration | Multi-user workspaces with role-based access | P3 |
| White-label | Resellable PostPilot for agencies | P3 |

---

## Team Communication

### Key Contacts

| Role | Responsibility |
|------|---------------|
| Backend Developer | API endpoints, services, database models, Celery tasks |
| Frontend Developer | Dashboard pages, landing page, UI components |
| QA Engineer | Test coverage, API verification, dashboard testing |
| DevOps | Docker, deployment, CI/CD, monitoring |

### Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| -- | Use config-driven dashboard | Single `service.config.ts` controls all branding; enables rapid white-label |
| -- | Mock OAuth in scaffold | Allows full testing without platform API credentials; real OAuth is Phase 1 |
| -- | Soft-delete for social accounts | Preserves post history and analytics after disconnect |
| -- | Sentinel value pattern (`...`) for updates | Distinguishes "not provided" from "set to None" in partial updates |
| -- | Separate landing page app | Decouples marketing site from authenticated dashboard; static export for CDN |
