# ContentForge

> AI Product Content Generator

## Overview

ContentForge is an independently hostable SaaS product that generates SEO-optimized
product titles, descriptions, meta tags, bullet points, and keywords using Claude AI.
It also handles product image download, optimization, and format conversion. Can be used
standalone or integrated with the dropshipping platform.

**For Developers:**
    Feature logic in `backend/app/services/content_service.py` (AI generation),
    `backend/app/services/image_service.py` (image processing via Pillow), and
    `backend/app/services/pricing_service.py` (markup calculator). Dashboard is
    config-driven via `dashboard/src/service.config.ts`.

**For Project Managers:**
    ContentForge is Feature A2 in the platform roadmap. Fully scaffolded with
    auth, billing, API keys, 45 backend tests, and 2 dashboard feature pages.
    Pricing: Free ($0), Pro ($19/mo), Enterprise ($79/mo).

**For QA Engineers:**
    Test the generation pipeline (create job → poll status → view content), template
    CRUD, image processing, bulk generation, and plan limit enforcement.

**For End Users:**
    Transform raw product URLs into polished, SEO-ready listings in seconds.
    Choose a tone and style template, generate content, and export to your store.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 | 8102 |
| Dashboard | Next.js 16 + Tailwind | 3102 |
| Landing Page | Next.js 16 (static) | 3202 |
| Database | PostgreSQL 16 | 5502 |
| Cache/Queue | Redis 7 | 6402 |
| Task Queue | Celery | — |

## Quick Start

```bash
make install && make migrate && make start
```

### Access Points
- **API**: http://localhost:8102 | **Docs**: http://localhost:8102/docs
- **Dashboard**: http://localhost:3102
- **Landing Page**: http://localhost:3202

## Core Features

### AI Content Generation
- **Content types**: SEO title, product description, meta description, keywords, bullet points
- **Claude API integration**: Contextual, high-quality copy generation
- **Template system**: Tone (professional, casual, luxury), style, and length presets
- **Bulk generation**: Import CSV or URL list for batch processing

### Image Optimization
- **Download + process**: Fetch product images from source URLs
- **Format conversion**: WebP output for modern browsers
- **Resize + compress**: Configurable dimensions and quality settings via Pillow

### Pricing Calculator
- **Configurable markup**: Set profit margins per product
- **Psychological rounding**: Smart price endings ($X.99, $X.95)

## API Endpoints

### Content Generation
```
POST /api/v1/content/generate            — Create generation job (enforces plan limits)
POST /api/v1/content/generate/bulk       — Bulk generate from URLs/CSV
GET  /api/v1/content/jobs                — List jobs with pagination
GET  /api/v1/content/jobs/{job_id}       — Get job with generated content items
DELETE /api/v1/content/jobs/{job_id}     — Delete job and content
PATCH /api/v1/content/{content_id}       — Edit generated content text
```

### Templates
```
POST   /api/v1/templates                 — Create custom template
GET    /api/v1/templates                 — List system + user templates
GET    /api/v1/templates/{template_id}   — Get template
PATCH  /api/v1/templates/{template_id}   — Update custom template
DELETE /api/v1/templates/{template_id}   — Delete custom template
```

### Images
```
GET    /api/v1/images                    — List processed images
GET    /api/v1/images/{image_id}         — Get image details
DELETE /api/v1/images/{image_id}         — Delete image record
```

## Pricing

| Tier | Price/mo | Generations | Words/Gen | AI Images | Templates |
|------|----------|------------|-----------|-----------|-----------|
| Free | $0 | 10/mo | 500 | 5 | Basic |
| Pro | $19 | 200/mo | 2,000 | 100 | All + Bulk import |
| Enterprise | $79 | Unlimited | Unlimited | Unlimited | All + API + White-label |

## Database Tables

| Table | Purpose |
|-------|---------|
| `users`, `api_keys`, `subscriptions` | Auth & billing (standard) |
| `generation_jobs` | Content generation job tracking |
| `generated_content` | Individual content items (title, description, meta, keywords) |
| `image_jobs` | Image download/optimization tracking |
| `templates` | System + user content templates (tone, style, prompt) |

## Testing

```bash
make test-backend    # 45 backend unit tests
```

## Design System

- **Primary**: Violet Purple — `oklch(0.60 0.22 300)` / `#8b5cf6`
- **Accent**: Soft Lavender — `oklch(0.75 0.18 280)` / `#a78bfa`
- **Heading font**: Clash Display (creative, bold)
- **Body font**: Satoshi

## License

Proprietary — All rights reserved.
