# RankPilot

> Automated SEO Engine

## Overview

RankPilot is an independently hostable SaaS product that automates search engine optimization
for e-commerce stores. It manages sitemaps, JSON-LD schema markup, AI-generated blog posts,
keyword rank tracking, and comprehensive SEO audits. Can be used standalone or integrated
with the dropshipping platform.

**For Developers:**
    Feature logic across `sites_service.py`, `blog_service.py`, `keyword_service.py`,
    `audit_service.py`, and `schema_service.py`. RankPilot has the most API endpoints
    of any service (5 route files, 20+ endpoints). Dashboard is config-driven via
    `dashboard/src/service.config.ts`.

**For Project Managers:**
    RankPilot is Feature A3. Fully scaffolded with 74 backend tests and 3 dashboard
    feature pages. Pricing: Free ($0), Pro ($29/mo), Enterprise ($99/mo).

**For QA Engineers:**
    Test site CRUD + domain verification, blog post generation + publishing, keyword
    tracking + rank refresh, SEO audit scoring, JSON-LD schema preview, and plan limits.

**For End Users:**
    Boost your store's search rankings automatically. Add your domain, generate SEO-optimized
    blog posts targeting your keywords, track your ranking positions, and fix issues found
    by automated audits.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 | 8103 |
| Dashboard | Next.js 16 + Tailwind | 3103 |
| Landing Page | Next.js 16 (static) | 3203 |
| Database | PostgreSQL 16 | 5503 |
| Cache/Queue | Redis 7 | 6403 |
| Task Queue | Celery | — |

## Quick Start

```bash
make install && make migrate && make start
```

### Access Points
- **API**: http://localhost:8103 | **Docs**: http://localhost:8103/docs
- **Dashboard**: http://localhost:3103
- **Landing Page**: http://localhost:3203

## Core Features

### Site Management
- Add domains for SEO tracking with ownership verification
- Sitemap.xml generation (products, categories, blog posts)
- Per-site keyword tracking and audit history

### AI Blog Post Generation
- Claude API generates keyword-targeted blog content
- Full post lifecycle: draft → published with slug management
- Meta description and keyword auto-extraction

### Keyword Rank Tracking
- Track keyword positions in search results over time
- Search volume and difficulty metrics
- Rank change detection (current vs. previous)

### SEO Audits
- Automated scoring of on-page SEO factors
- Issue detection: missing titles, meta descriptions, heading structure, image alt tags
- Actionable recommendations per issue
- Content gap analysis

### JSON-LD Schema Markup
- Generate structured data for Product, AggregateRating, Offer, BreadcrumbList
- Per-page-type schema configuration
- Live preview of generated `<script>` tags

## API Endpoints

### Sites
```
POST   /api/v1/sites                     — Create site (domain for SEO tracking)
GET    /api/v1/sites                     — List sites with pagination
GET    /api/v1/sites/{site_id}           — Get site details
PATCH  /api/v1/sites/{site_id}           — Update site info
DELETE /api/v1/sites/{site_id}           — Delete site + all related data
POST   /api/v1/sites/{site_id}/verify    — Verify domain ownership
```

### Blog Posts
```
POST   /api/v1/blog-posts               — Create blog post (enforces plan limits)
GET    /api/v1/blog-posts               — List with site filter + pagination
GET    /api/v1/blog-posts/{post_id}     — Get post details
PATCH  /api/v1/blog-posts/{post_id}     — Update post fields
DELETE /api/v1/blog-posts/{post_id}     — Delete post
POST   /api/v1/blog-posts/generate      — Generate AI content for post
```

### Keywords
```
POST   /api/v1/keywords                 — Add keyword to track (enforces limits)
GET    /api/v1/keywords                 — List keywords by site + pagination
DELETE /api/v1/keywords/{keyword_id}    — Remove keyword
POST   /api/v1/keywords/refresh         — Refresh keyword ranks
```

### Audits
```
POST /api/v1/audits/run                 — Run SEO audit (score + issues + recommendations)
GET  /api/v1/audits                     — List audit history by site
GET  /api/v1/audits/{audit_id}          — Get audit details
```

### Schema Markup
```
POST   /api/v1/schema                   — Create JSON-LD schema config
GET    /api/v1/schema                   — List schema configs by site
GET    /api/v1/schema/{config_id}       — Get schema config
PATCH  /api/v1/schema/{config_id}       — Update schema
DELETE /api/v1/schema/{config_id}       — Delete schema
GET    /api/v1/schema/{config_id}/preview — Preview JSON-LD script tag
```

## Pricing

| Tier | Price/mo | Blog Posts | Keywords Tracked | Sites | Schema Markup |
|------|----------|-----------|-----------------|-------|---------------|
| Free | $0 | 2/mo | 20 | 1 | Basic |
| Pro | $29 | 20/mo | 200 | 5 | Advanced JSON-LD + Content gap |
| Enterprise | $99 | Unlimited | Unlimited | Unlimited | Full + API + Custom schema |

## Database Tables

| Table | Purpose |
|-------|---------|
| `users`, `api_keys`, `subscriptions` | Auth & billing (standard) |
| `sites` | Domains being tracked for SEO |
| `blog_posts` | AI-generated blog content with publishing status |
| `keyword_tracking` | Keyword rank positions over time |
| `seo_audits` | Audit results with score, issues, recommendations |
| `schema_configs` | JSON-LD structured data configurations |

## Testing

```bash
make test-backend    # 74 backend unit tests
```

## Design System

- **Primary**: Emerald Green — `oklch(0.65 0.18 155)` / `#10b981`
- **Accent**: Light Green — `oklch(0.72 0.15 140)` / `#34d399`
- **Heading font**: General Sans (clean, trustworthy)
- **Body font**: Inter

## License

Proprietary — All rights reserved.
