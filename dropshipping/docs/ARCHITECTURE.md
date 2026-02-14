# Architecture

> Part of [Dropshipping Platform](README.md) documentation

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| Database | PostgreSQL | 16 |
| Migrations | Alembic (async) | 1.14+ |
| Task queue | Celery + Redis | 5.4+ |
| Auth | python-jose (JWT) + bcrypt | — |
| Billing | Stripe (mock mode supported) | — |
| Frontend framework | Next.js (App Router) | 16 |
| UI components | Shadcn/ui (dashboard only) | — |
| Styling | Tailwind CSS | 4 |
| Animation | Motion (framer-motion) | 12.33+ |
| Charts | Recharts | 2.x |
| Language | TypeScript | 5+ |
| E2E testing | Playwright | latest |
| Backend testing | pytest + httpx | 8.3+ |

## Project Structure

```
dropshipping/backend/
├── app/
│   ├── main.py              # FastAPI app + 36 router registrations
│   ├── config.py            # pydantic-settings (reads env vars)
│   ├── database.py          # Async engine, session factory, Base
│   ├── api/                 # FastAPI routers (36 files)
│   │   ├── auth.py, deps.py, public.py, stores.py, products.py, orders.py
│   │   ├── bridge.py        # ServiceBridge REST API (5 endpoints)
│   │   └── ... (categories, discounts, themes, analytics, reviews, etc.)
│   ├── models/              # SQLAlchemy models (22 files, ~37 tables)
│   │   ├── user.py, store.py, product.py, order.py, customer.py, theme.py
│   │   ├── bridge_delivery.py  # BridgeDelivery ORM model
│   │   └── ... (subscription, discount, category, review, etc.)
│   ├── schemas/             # Pydantic request/response schemas (27 files)
│   ├── services/            # Business logic (30 files)
│   │   ├── bridge_service.py   # HMAC signing, async query helpers
│   │   └── ... (auth, store, product, order, theme, analytics, etc.)
│   ├── constants/themes.py  # Block types (13), preset themes (11), typography
│   ├── tasks/               # Celery tasks (7 modules, 21 tasks)
│   │   ├── bridge_tasks.py  # ServiceBridge event dispatch with HMAC
│   │   └── ... (email, webhook, notification, fraud, order, analytics)
│   └── utils/slug.py        # slugify() + generate_unique_slug(exclude_id=)
├── alembic/versions/        # 13 migration files
└── tests/                   # ~35 test files, 580 tests

dropshipping/dashboard/src/
├── app/                     # 34 pages (auth, stores, products, orders, themes, etc.)
│   └── stores/[id]/services/activity/  # ServiceBridge activity log
├── components/              # Shell, sidebar, motion wrappers, service widgets
└── lib/api.ts, auth.ts      # API client, token management

dropshipping/storefront/src/
├── app/                     # 18 pages (products, cart, checkout, account, etc.)
├── components/blocks/       # 13 theme block renderers
├── components/motion-primitives.tsx  # FadeIn, StaggerChildren, SlideIn, etc.
└── lib/theme-utils.ts       # CSS variable generation from theme config
```

## ServiceBridge — Platform Event Integration

The ServiceBridge dispatches platform lifecycle events to connected SaaS services via HMAC-signed HTTP webhooks through Celery background tasks.

### Event Dispatch Flow

1. API handler (e.g. `products.py`) calls `fire_platform_event()` after CRUD
2. `fire_platform_event()` lazy-imports and calls `dispatch_platform_event.delay()`
3. Celery task queries `ServiceIntegration` for connected services
4. Filters by `EVENT_SERVICE_MAP` (5 event types mapped to service lists)
5. POSTs to each service with HMAC-SHA256 signature header
6. Records `BridgeDelivery` row for each attempt (success/failure, latency)

### Event-Service Mapping

| Event | Services |
|-------|---------|
| `product.created` | ContentForge, RankPilot, TrendScout, PostPilot, AdScale, ShopChat |
| `product.updated` | ContentForge, RankPilot, ShopChat |
| `order.created` | FlowSend, SpyDrop |
| `order.shipped` | FlowSend |
| `customer.created` | FlowSend |

### Key Files

| File | Purpose |
|------|---------|
| `app/tasks/bridge_tasks.py` | Celery task with `EVENT_SERVICE_MAP` |
| `app/services/bridge_service.py` | HMAC signing, async query helpers |
| `app/api/bridge.py` | REST API (5 endpoints) for dashboard |
| `app/models/bridge_delivery.py` | `BridgeDelivery` ORM model |
| `app/schemas/bridge.py` | Pydantic schemas |

### Dashboard Components

| Component | Purpose |
|-----------|---------|
| `service-activity-card.tsx` | Reusable delivery list widget |
| `resource-service-status.tsx` | 8-service status grid |
| `stores/[id]/services/activity/page.tsx` | Full activity log with KPIs |

## Background Tasks (Celery)

21 task functions across 7 modules:

| Module | Tasks | Purpose |
|--------|-------|---------|
| `bridge_tasks.py` | 1 | ServiceBridge event dispatch with HMAC |
| `email_tasks.py` | 9 | Transactional emails |
| `webhook_tasks.py` | 1 | Store webhook delivery |
| `notification_tasks.py` | 4 | Dashboard notifications |
| `fraud_tasks.py` | 1 | Fraud risk scoring |
| `order_tasks.py` | 3 | Order orchestration + auto-fulfill |
| `analytics_tasks.py` | 2 | Daily analytics + cleanup |

Workers use `SyncSessionFactory` (psycopg2), not asyncpg. Always pass UUIDs as strings to `.delay()`.

## Theme System

### Block Types (13)

| Block Type | Purpose |
|-----------|---------|
| `hero_banner` | Hero section with gradient, image, or product showcase |
| `featured_products` | Grid of featured products |
| `categories_grid` | Category browsing grid |
| `product_carousel` | Auto-scrolling carousel with snap points |
| `testimonials` | Customer testimonials (cards or slider) |
| `countdown_timer` | Sale/launch countdown |
| `video_banner` | YouTube/Vimeo embed with overlay |
| `trust_badges` | Trust indicators (shipping, security, guarantee) |
| `reviews` | Customer review grid |
| `newsletter` | Email subscription section |
| `custom_text` | Custom HTML/text content |
| `image_banner` | Static image with text overlay |
| `spacer` | Vertical spacing |

### Preset Themes (11)

| Theme | Vibe | Primary Color | Heading Font |
|-------|------|--------------|-------------|
| Frosted (default) | Clean, modern | Teal | Bricolage Grotesque |
| Midnight | Dark, sleek | Cyan | Syne |
| Botanical | Organic, natural | Forest Green | Fraunces |
| Neon | Electric, bold | Hot Pink | Unbounded |
| Luxe | Premium, elegant | Gold | Playfair Display |
| Playful | Fun, vibrant | Orange | Outfit |
| Industrial | Raw, utilitarian | Charcoal | Archivo Black |
| Coastal | Airy, beach | Ocean Blue | Josefin Sans |
| Monochrome | Minimal, editorial | Black | DM Serif Display |
| Cyberpunk | Futuristic, neon | Electric Purple | Unbounded |
| Terracotta | Earthy, warm | Terracotta | Bitter |

Theme CSS variables are generated via `storefront/src/lib/theme-utils.ts` (`--theme-primary`, `--theme-heading-font`, etc.).

## Animation System

Motion primitives in `storefront/src/components/motion-primitives.tsx`:

| Primitive | Effect |
|-----------|--------|
| `FadeIn` | Opacity 0→1 + translateY(20px→0) |
| `StaggerChildren` | Wraps children with staggered delays (50-80ms) |
| `SlideIn` | Slide from configurable direction |
| `ScaleIn` | Scale 0.95→1 with opacity |
| `ScrollReveal` | Triggers animation on viewport entry |

Dashboard uses `motion-wrappers.tsx` for staggered card entrances and animated counters.

## Key Design Decisions

1. **Multi-tenant isolation:** All store-scoped queries filter by `store_id` + owner `user_id`. Enforced at the service layer.
2. **Mock Stripe:** When `STRIPE_SECRET_KEY` is not configured, Stripe returns mock responses for full local dev.
3. **Block-based themes:** Storefront pages are composed of configurable blocks, not hardcoded layouts.
4. **CSS variable theming:** All theme values applied via CSS custom properties for runtime switching.
5. **Customer accounts:** Separate from store-owner accounts with their own JWT tokens.
6. **ServiceBridge async dispatch:** Events dispatched via Celery to avoid blocking API responses. Each delivery signed with HMAC-SHA256 and logged as a `BridgeDelivery` record.

---
*See also: [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
