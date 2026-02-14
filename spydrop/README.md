# SpyDrop

> Competitor Intelligence

## Overview

SpyDrop is an independently hostable SaaS product that monitors competitor stores,
tracks product catalogs and price changes, sends alerts on significant changes, and
performs reverse source-finding to identify suppliers. Can be used standalone or
integrated with the dropshipping platform.

**For Developers:**
    Feature logic in `competitor_service.py` (store scraping via Playwright headless),
    `product_service.py` (catalog diff detection), and `alert_service.py` (notification
    triggers). Dashboard is config-driven via `dashboard/src/service.config.ts`.

**For Project Managers:**
    SpyDrop is Feature A5. Fully scaffolded with 43 backend tests and 2 dashboard
    feature pages. Pricing: Free ($0), Pro ($29/mo), Enterprise ($99/mo).

**For QA Engineers:**
    Test competitor CRUD, product catalog tracking with price history, alert
    configuration, scan scheduling, and plan limit enforcement on competitor count.

**For End Users:**
    Stay ahead of your competition. Monitor their product catalogs, get alerted when
    they change prices or add new products, and find the original suppliers to source
    the same products at cost.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 | 8105 |
| Dashboard | Next.js 16 + Tailwind | 3105 |
| Landing Page | Next.js 16 (static) | 3205 |
| Database | PostgreSQL 16 | 5505 |
| Cache/Queue | Redis 7 | 6405 |
| Task Queue | Celery | — |

## Quick Start

```bash
make install && make migrate && make start
```

### Access Points
- **API**: http://localhost:8105 | **Docs**: http://localhost:8105/docs
- **Dashboard**: http://localhost:3105
- **Landing Page**: http://localhost:3205

## Core Features

### Competitor Monitoring
- Add competitor store URLs for automated tracking
- Configurable scan frequency: weekly (Free), daily (Pro), hourly (Enterprise)
- Platform detection (Shopify, WooCommerce, custom)
- Scan history with new/removed product counts

### Product Catalog Tracking
- Automatic diff detection: new products, removed products, price changes
- Full price history with timestamps
- Cross-competitor product aggregation and filtering
- Sortable by price, first seen date, last seen date

### Alert System
- Price drop alerts with configurable thresholds
- New product alerts per competitor
- Out-of-stock notifications
- Email delivery for triggered alerts

### Reverse Source Finding
- Match competitor products to original suppliers
- Reverse image search and title matching
- Confidence scoring on source matches
- Bulk sourcing for Enterprise tier

## API Endpoints

### Competitors
```
POST   /api/v1/competitors                          — Create competitor (enforces plan limits)
GET    /api/v1/competitors                          — List competitors with pagination
GET    /api/v1/competitors/{competitor_id}           — Competitor details
PATCH  /api/v1/competitors/{competitor_id}           — Update settings
DELETE /api/v1/competitors/{competitor_id}           — Delete + cascade data
GET    /api/v1/competitors/{competitor_id}/products  — List competitor products
```

### Products
```
GET /api/v1/products                    — List all products across competitors (filterable)
GET /api/v1/products/{product_id}       — Product details with price history
```

## Pricing

| Tier | Price/mo | Competitor Stores | Scan Frequency | Price Alerts | Source Finding |
|------|----------|------------------|----------------|--------------|----------------|
| Free | $0 | 3 | Weekly | No | No |
| Pro | $29 | 25 | Daily | Yes | Yes |
| Enterprise | $99 | Unlimited | Hourly | Yes + API | Yes + Bulk |

## Database Tables

| Table | Purpose |
|-------|---------|
| `users`, `api_keys`, `subscriptions` | Auth & billing (standard) |
| `competitors` | Monitored competitor stores with scan config |
| `competitor_products` | Tracked products with price history (JSON array) |
| `price_alerts` | Alert rules (price drop, new product, out-of-stock) |
| `scan_results` | Scan execution logs with diff counts |
| `source_matches` | Reverse-matched supplier sources with confidence scores |

## Testing

```bash
make test-backend    # 43 backend unit tests
```

## Design System

- **Primary**: Slate Cyan — `oklch(0.60 0.15 220)` / `#06b6d4`
- **Accent**: Light Cyan — `oklch(0.70 0.12 210)` / `#67e8f9`
- **Heading font**: Geist (technical, modern)
- **Body font**: Geist

## License

Proprietary — All rights reserved.
