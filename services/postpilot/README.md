# PostPilot

> Social Media Automation

## Overview

PostPilot is an independently hostable SaaS product for automating social media posting
across Instagram, Facebook, and TikTok. It generates AI-powered captions and hashtags,
manages a content queue from product data, handles scheduling, and tracks post performance
metrics. Can be used standalone or integrated with the dropshipping platform.

**For Developers:**
    Feature logic in `account_service.py` (OAuth connections), `post_service.py` (scheduling),
    `queue_service.py` (AI content queue), and `analytics_service.py` (metrics aggregation).
    Dashboard is config-driven via `dashboard/src/service.config.ts`.

**For Project Managers:**
    PostPilot is Feature A6. Fully scaffolded with 62 backend tests and 3 dashboard
    feature pages. Pricing: Free ($0), Pro ($29/mo), Enterprise ($99/mo).

**For QA Engineers:**
    Test social account connection, post lifecycle (draft → scheduled → posted), content
    queue with AI caption generation, calendar view, analytics metrics, and plan limits.

**For End Users:**
    Automate your social media presence. Connect your accounts, generate AI captions
    from your products, schedule posts across platforms, and track engagement metrics
    from a single dashboard.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 | 8106 |
| Dashboard | Next.js 16 + Tailwind | 3106 |
| Landing Page | Next.js 16 (static) | 3206 |
| Database | PostgreSQL 16 | 5506 |
| Cache/Queue | Redis 7 | 6406 |
| Task Queue | Celery | — |

## Quick Start

```bash
make install && make migrate && make start
```

### Access Points
- **API**: http://localhost:8106 | **Docs**: http://localhost:8106/docs
- **Dashboard**: http://localhost:3106
- **Landing Page**: http://localhost:3206

## Core Features

### Social Account Management
- OAuth connection for Instagram, Facebook, TikTok
- Encrypted token storage (access + refresh tokens)
- Per-account status tracking

### Post Creation & Scheduling
- Create posts with content, media URLs, and hashtags
- Platform-specific formatting
- Schedule posts for future publication
- Calendar view of scheduled content

### AI Content Queue
- Auto-generate social content from product data
- Claude API for platform-specific captions and hashtags
- Queue workflow: pending → AI generated → approved/rejected → scheduled
- Standalone caption generation endpoint

### Post Analytics
- Per-post metrics: impressions, reach, likes, comments, shares, clicks
- Aggregate analytics overview across accounts
- Platform comparison charts

## API Endpoints

### Social Accounts
```
POST   /api/v1/accounts                  — Connect social account (Instagram/Facebook/TikTok)
GET    /api/v1/accounts                  — List connected accounts
DELETE /api/v1/accounts/{account_id}     — Disconnect account
```

### Posts
```
POST   /api/v1/posts                     — Create post (enforces plan limits)
GET    /api/v1/posts                     — List with status/platform filter
GET    /api/v1/posts/calendar            — Calendar view by date range
GET    /api/v1/posts/{post_id}           — Post details
PATCH  /api/v1/posts/{post_id}           — Update post (draft/scheduled only)
DELETE /api/v1/posts/{post_id}           — Delete post
POST   /api/v1/posts/{post_id}/schedule  — Schedule post for publication
```

### Content Queue
```
POST   /api/v1/queue                     — Add product to content queue
GET    /api/v1/queue                     — List queue items with status filter
GET    /api/v1/queue/{item_id}           — Queue item details
DELETE /api/v1/queue/{item_id}           — Delete queue item
POST   /api/v1/queue/{item_id}/generate  — Generate AI caption for item
POST   /api/v1/queue/{item_id}/approve   — Approve for scheduling
POST   /api/v1/queue/{item_id}/reject    — Reject item
POST   /api/v1/queue/generate-caption    — Generate caption standalone
```

### Analytics
```
GET /api/v1/analytics/overview           — Aggregated analytics
GET /api/v1/analytics/posts              — Metrics for all posts
GET /api/v1/analytics/posts/{post_id}    — Metrics for single post
```

## Pricing

| Tier | Price/mo | Posts/mo | Platforms | AI Captions | Scheduling |
|------|----------|---------|-----------|-------------|------------|
| Free | $0 | 10 | 1 | 5/mo | Manual only |
| Pro | $29 | 200 | All 3 | Unlimited | Auto-schedule |
| Enterprise | $99 | Unlimited | All + API | Unlimited + hashtags | Auto + Analytics |

## Database Tables

| Table | Purpose |
|-------|---------|
| `users`, `api_keys`, `subscriptions` | Auth & billing (standard) |
| `social_accounts` | Connected platforms with encrypted OAuth tokens |
| `posts` | Social media posts with scheduling and status |
| `post_metrics` | Engagement metrics per post (impressions, likes, etc.) |
| `content_queue` | AI-generated content pipeline from product data |

## Testing

```bash
make test-backend    # 62 backend unit tests
```

## Design System

- **Primary**: Hot Pink — `oklch(0.65 0.22 350)` / `#ec4899`
- **Accent**: Soft Pink — `oklch(0.72 0.18 330)` / `#f472b6`
- **Heading font**: Plus Jakarta Sans (social, vibrant)
- **Body font**: Inter

## License

Proprietary — All rights reserved.
