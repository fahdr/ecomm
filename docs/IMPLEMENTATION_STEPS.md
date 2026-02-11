# Implementation Steps

**For Developers & Project Managers:**
Step-by-step implementation guide for each feature in the dropshipping platform.
Features are ordered by dependency and were completed sequentially.

---

## Feature 1: Project Scaffolding & Local Dev Environment

**Status:** Complete

### What was built
Foundational project structure — all three apps runnable inside the devcontainer.

### Steps completed
1. Created FastAPI backend with `pyproject.toml` and all core dependencies (FastAPI, SQLAlchemy, Alembic, Celery, passlib, python-jose, httpx)
2. Created `app/config.py` — pydantic-settings class reading env vars from docker-compose
3. Created `app/database.py` — async SQLAlchemy engine, session factory, `Base` class, and `get_db` dependency
4. Initialized Alembic with async `env.py` that reads from `app.config.settings`
5. Created `app/tasks/celery_app.py` — Celery instance with Redis broker and autodiscovery
6. Created `GET /api/v1/health` endpoint that pings the database
7. Created `tests/conftest.py` with `client` fixture (httpx AsyncClient + ASGITransport)
8. Created `tests/test_health.py` — 1 passing test
9. Scaffolded Next.js 16 dashboard with Shadcn/ui and Tailwind
10. Scaffolded Next.js 16 storefront with Tailwind
11. Created API client utilities (`src/lib/api.ts`) in both frontend apps

### Verification
- `pytest` — 1 passing test
- `curl localhost:8000/api/v1/health` — returns `{"status": "ok"}`
- `npm run build` in dashboard and storefront — both compile successfully
- Celery worker connects to Redis and logs ready

---

## Feature 2: User Authentication

**Status:** Complete

### What was built
Registration, login, JWT access/refresh tokens, a protected `/me` endpoint, dashboard login/register pages, auth context with token refresh, and route protection.

### Backend steps completed
1. Created `app/models/user.py` — `User` model with id, email, hashed_password, is_active, created_at, updated_at
2. Generated Alembic migration for `users` table (`alembic revision --autogenerate`)
3. Applied migration (`alembic upgrade head`)
4. Created `app/schemas/auth.py` — Pydantic schemas: RegisterRequest, LoginRequest, TokenResponse, UserResponse
5. Created `app/services/auth_service.py` — business logic for register, login, token creation, token verification, refresh
6. Created `app/api/deps.py` — `get_current_user` FastAPI dependency (decodes JWT, fetches user)
7. Created `app/api/auth.py` — auth router with endpoints: register, login, refresh, me
8. Registered auth router in `app/main.py`
9. Created `tests/test_auth.py` — tests for all auth endpoints
10. Updated `tests/conftest.py` with DB isolation (table truncation between tests)

### Frontend steps completed
1. Installed Shadcn/ui components: `npx shadcn@latest add button input label card`
2. Created `dashboard/src/lib/auth.ts` — cookie-based token storage (get/set/clear)
3. Created `dashboard/src/contexts/auth-context.tsx` — AuthProvider wraps app, provides user state, login/logout/register, automatic token refresh
4. Built registration page at `dashboard/src/app/(auth)/register/page.tsx` — form with email + password, calls register API, stores tokens, redirects to `/`
5. Built login page at `dashboard/src/app/(auth)/login/page.tsx` — form with email + password, calls login API, stores tokens, redirects to `/`
6. Created route protection proxy (`dashboard/src/proxy.ts`) — checks for access_token cookie, redirects unauthenticated users to `/login`
7. Updated dashboard home page with logout button and user email display
8. Wrapped app in AuthProvider in root layout, wired `api.setToken()` in auth context

### Verification
- `npm run build` — compiles without errors
- `pytest` — 16 backend tests pass
- Register → auto-login → dashboard shows user email → logout → redirected to login

---

## Feature 3: Store Creation (Backend + Dashboard)

**Status:** Complete

### What was built
Full CRUD for stores with tenant isolation — users can only access their own stores. Dashboard pages for creating, listing, editing, and deleting stores.

### Backend steps completed
1. Created `app/models/store.py` — `Store` model with id (UUID), user_id (FK), name, slug (unique), niche, description, status (enum: active/paused/deleted), created_at, updated_at, plus relationship to User
2. Created `app/utils/slug.py` — `slugify()` for URL-safe strings + `generate_unique_slug()` with collision resolution (-2, -3, etc.)
3. Generated and applied Alembic migration for `stores` table (with indexes on slug and user_id)
4. Created `app/schemas/store.py` — CreateStoreRequest, UpdateStoreRequest (partial), StoreResponse
5. Created `app/services/store_service.py` — create_store, list_stores (excludes deleted), get_store (ownership check), update_store (with slug regen), delete_store (soft-delete)
6. Created `app/api/stores.py` — store router with POST, GET (list), GET/{id}, PATCH/{id}, DELETE/{id}
7. Registered store router in `app/main.py`, imported Store in `app/models/__init__.py`
8. Created `tests/test_stores.py` — 20 tests covering CRUD, slug uniqueness, auth, validation, soft-delete, and tenant isolation

### Frontend steps completed
1. Built store list page at `dashboard/src/app/stores/page.tsx` — card grid with status badges, empty state, "Create Store" button
2. Built create store page at `dashboard/src/app/stores/new/page.tsx` — form with name, niche dropdown, description textarea
3. Built store settings page at `dashboard/src/app/stores/[id]/page.tsx` — edit form with all fields, status toggle, delete button with confirmation dialog
4. Updated dashboard home page with "Stores" nav link and "Go to Stores" CTA button

### Verification
- `pytest` — 36 tests pass
- `npm run build` — compiles without errors
- CRUD operations: create → list → get → update → soft-delete all working
- Tenant isolation: user A cannot see/edit/delete user B's stores

---

## Feature 4: Storefront (Public-Facing Store)

**Status:** Complete

### What was built
Public-facing storefront that resolves stores by slug and renders store-branded pages with dynamic SEO metadata.

### Backend steps completed
1. Created `app/schemas/public.py` — `PublicStoreResponse` schema (excludes `user_id` for security)
2. Created `app/api/public.py` — public router with `GET /api/v1/public/stores/{slug}` (only returns active stores)
3. Registered public router in `app/main.py`
4. Created `tests/test_public.py` — 6 tests

### Frontend steps completed
1. Created storefront types, store resolution, middleware, and context
2. Built storefront layout with dynamic header/footer and SEO metadata
3. Built homepage with hero section and product grid placeholder
4. Built 404 page for unknown stores

### Verification
- `pytest` — 42 tests pass
- `npm run build` — compiles without errors
- Local dev: `localhost:3001?store=my-slug` resolves store and renders branded page

---

## Feature 5: Product Management (Manual CRUD)

**Status:** Complete

### What was built
Full product CRUD with variants, image upload, pagination, search, and status filtering. Dashboard and storefront product pages.

### Backend steps completed
1. Created `app/models/product.py` — `Product` + `ProductVariant` models
2. Created schemas, services, and API routes for products
3. Added public product endpoints (active only, excludes cost)
4. Created `tests/test_products.py` — 24 tests

### Frontend steps completed
1. Dashboard: product list, create, edit pages with image upload and variant management
2. Storefront: product grid, listing page with pagination, detail page with gallery

### Verification
- `pytest` — 66 tests pass
- Both frontends build cleanly with new product routes

---

## Feature 6: Shopping Cart & Customer Checkout

**Status:** Complete

### What was built
Client-side shopping cart with localStorage persistence, Stripe Checkout integration (with mock mode), order management for store owners.

### Backend steps completed
1. Created `app/models/order.py` — `Order` + `OrderItem` models with price/title snapshots
2. Created order service with checkout validation, status transitions, inventory management
3. Created Stripe service with mock mode when no API key configured
4. Created webhook handler for `checkout.session.completed`
5. Created `tests/test_orders.py` — 21 tests

### Frontend steps completed
1. Storefront: CartProvider, cart page, add-to-cart component, checkout success page
2. Dashboard: order list and detail pages with status management

### Verification
- `pytest` — 87 tests pass
- Cart → checkout → order confirmation flow works end-to-end

---

## Feature 7: Stripe Subscriptions (SaaS Billing)

**Status:** Complete

### What was built
SaaS billing with three subscription tiers (Starter/Growth/Pro), plan limit enforcement, and customer portal integration.

### Steps completed
1. Created `app/models/subscription.py` — Subscription model with Stripe integration
2. Extended Stripe service with subscription checkout and portal sessions
3. Added webhook handlers for subscription lifecycle events
4. Created plan enforcement middleware in `app/api/deps.py`
5. Created subscription API endpoints
6. Dashboard: pricing page (3-tier comparison), billing page (current plan, portal link)
7. Plan limit enforcement in UI (disable store/product creation at limits)

---

## Phase 1 Extended: Features 8-30

**Status:** All Complete

All 23 additional features were implemented in a single comprehensive phase. Each feature follows the same pattern: model → schema → service → API router → tests → dashboard page → storefront integration (where applicable).

### Features implemented

| # | Feature | Key Files |
|---|---------|-----------|
| 8 | Categories | `models/category.py`, `services/category_service.py`, `api/categories.py` |
| 9 | Reviews & Ratings | `models/review.py`, `services/review_service.py`, `api/reviews.py` |
| 10 | Analytics | `services/analytics_service.py`, `api/analytics.py` |
| 11 | Discounts & Coupons | `models/discount.py`, `services/discount_service.py`, `api/discounts.py` |
| 12 | Gift Cards | `models/gift_card.py`, `services/gift_card_service.py`, `api/gift_cards.py` |
| 13 | Theme System | `models/theme.py`, `services/theme_service.py`, `api/themes.py`, `constants/themes.py` |
| 14 | Customer Accounts | `models/customer.py`, `services/customer_service.py`, `api/customer_auth.py` |
| 15 | Store Themes (Full) | Theme presets, block system, CSS variable generation |
| 16 | Refunds | `models/refund.py`, `services/refund_service.py`, `api/refunds.py` |
| 17 | Tax Configuration | `models/tax.py`, `services/tax_service.py`, `api/tax.py` |
| 18 | Currency Settings | `services/currency_service.py`, `api/currency.py` |
| 19 | Custom Domains | `models/domain.py`, `services/domain_service.py`, `api/domains.py` |
| 20 | Team Management | `models/team.py`, `services/team_service.py`, `api/teams.py` |
| 21 | Webhooks | `models/webhook.py`, `services/webhook_service.py`, `api/store_webhooks.py` |
| 22 | A/B Tests | `models/ab_test.py`, `services/ab_test_service.py`, `api/ab_tests.py` |
| 23 | Customer Segments | `models/segment.py`, `services/segment_service.py`, `api/segments.py` |
| 24 | Supplier Management | `models/supplier.py`, `services/supplier_service.py`, `api/suppliers.py` |
| 25 | Bulk Operations | `services/bulk_service.py`, `api/bulk.py` |
| 26 | Fraud Detection | `models/fraud.py`, `services/fraud_service.py`, `api/fraud.py` |
| 27 | Email Templates | `services/email_service.py` |
| 28 | Search | `services/search_service.py`, `api/search.py` |
| 29 | Notifications | `models/notification.py`, `services/notification_service.py`, `api/notifications.py` |
| 30 | Upsells | `models/upsell.py`, `services/upsell_service.py`, `api/upsells.py` |

### Verification
- `pytest` — 193 backend tests pass across 28 test files
- Dashboard builds cleanly with 34 pages
- Storefront builds cleanly with 18 pages

---

## Polish Plan (Phases A-G)

**Status:** All Complete

### Phase A: Order Enhancements

**What was built:** Full order fulfillment lifecycle with tracking.

1. Added `tracking_number`, `carrier`, `shipped_at`, `delivered_at` fields to Order model
2. New Alembic migration for order tracking fields
3. Created `POST /stores/{id}/orders/{orderId}/fulfill` endpoint
4. Updated order detail page with fulfillment UI (tracking number input, ship/deliver buttons)
5. Added shipping address display on order detail
6. Status transitions: pending → paid → shipped → delivered with validation

### Phase B: Customer Accounts

**What was built:** Full customer authentication and account management for storefronts.

1. Created `app/api/customer_auth.py` — register, login, me endpoints with customer-specific JWT
2. Created `app/api/customer_orders.py` — customer order history
3. Created `app/api/customer_addresses.py` — address book CRUD
4. Created `app/api/customer_wishlist.py` — wishlist management
5. Created `app/services/customer_service.py` — customer business logic
6. Storefront: account pages (login, register, orders, wishlist, addresses, settings)
7. Storefront: auth context with customer token management
8. Created `tests/test_customers.py`

### Phase C: Storefront Improvements

**What was built:** Search autocomplete, policies pages, mobile menu.

1. Created `storefront/src/components/header-search.tsx` — search autocomplete with product thumbnails
2. Created `storefront/src/app/policies/[slug]/page.tsx` — legal policy pages
3. Created `storefront/src/components/mobile-menu.tsx` — responsive mobile navigation
4. Updated storefront layout with mobile menu and search integration

### Phase D: Dashboard UI Overhaul

**What was built:** Professional dashboard shell with sidebar, top bar, and consistent layout.

1. Created `dashboard/src/components/sidebar.tsx` — collapsible sidebar with platform/store modes, 5 nav groups, active state, badges
2. Created `dashboard/src/components/top-bar.tsx` — top navigation bar
3. Created `dashboard/src/components/dashboard-shell.tsx` — shell wrapper combining sidebar + top bar
4. Created `dashboard/src/components/authenticated-layout.tsx` — auth guard HOC
5. Implemented OKLCH design system: teal primary, amber accent, Bricolage Grotesque + Instrument Sans + IBM Plex Mono fonts
6. Updated all 34 dashboard pages to use consistent shell layout

### Phase E: Store Improvements

**What was built:** Store context and navigation improvements.

1. Created `dashboard/src/contexts/store-context.tsx` — StoreProvider for store-scoped pages
2. Added breadcrumb navigation throughout store pages

### Phase F: Seed Data

**What was built:** Comprehensive demo data for the Volt Electronics store.

1. Created `scripts/seed.ts` — TypeScript seed script
2. Seeds: user, store, categories, products with variants, orders, reviews, themes
3. Idempotent execution (checks for existing records)

### Phase G: E2E Test Coverage

**What was built:** Comprehensive Playwright test suite.

1. Created `e2e/tests/helpers.ts` — shared test utilities
2. Created 23 spec files covering all major features
3. 171 e2e tests passing across dashboard and storefront

---

## Phase 2 Polish (Phases 1-5)

**Status:** All Complete

### Phase 2.1: Theme Engine v2

**What was built:** 5 new block types, hero product showcase, block config editor, 4 new preset themes.

#### New Block Types
1. Created `storefront/src/components/blocks/product-carousel.tsx` — horizontal scroll with snap, auto-advance, dots navigation
2. Created `storefront/src/components/blocks/testimonials.tsx` — card grid or animated slider with customer quotes
3. Created `storefront/src/components/blocks/countdown-timer.tsx` — live countdown (days/hours/min/sec), client component
4. Created `storefront/src/components/blocks/video-banner.tsx` — responsive YouTube/Vimeo embed with overlay text
5. Created `storefront/src/components/blocks/trust-badges.tsx` — icon grid (Truck, Shield, RotateCcw Lucide icons)
6. Updated `storefront/src/components/blocks/block-renderer.tsx` — registered all 5 new components in BLOCK_MAP
7. Updated `backend/app/constants/themes.py` — added 5 entries to BLOCK_TYPES with config schemas

#### Hero Banner Enhancement
8. Modified `storefront/src/components/blocks/hero-banner.tsx`:
   - Added `bg_type: "product_showcase"` mode
   - Featured product display with images, names, prices, "Shop Now" CTA
   - Overlay styles: gradient, blur, dark, none
   - Text position: left, center, right
   - Height options: sm, md, lg, full

#### Block Config Editor
9. Modified `dashboard/src/app/stores/[id]/themes/[themeId]/page.tsx`:
   - Replaced toggle list with expandable config panels per block
   - Each block type gets a specific config form (title, colors, product selection, layout, etc.)
   - "Add Block" button with block type picker
   - "Remove Block" with confirmation
   - Color picker: native `<input type="color">` + hex input

#### New Preset Themes
10. Added to `backend/app/constants/themes.py`:
    - **Coastal** — Ocean Blue (#1e6091), Josefin Sans, airy beach aesthetic
    - **Monochrome** — Black (#111111), DM Serif Display, minimal editorial
    - **Cyberpunk** — Electric Purple (#7c3aed), neon green accent, futuristic
    - **Terracotta** — Terracotta (#c2703e), Bitter font, earthy warm

#### Enhanced Typography
11. Added typography controls to theme config:
    - Font weight dropdown (300-700) for heading and body
    - Letter spacing: tight / normal / wide
    - Line height: compact / normal / relaxed
12. Updated `storefront/src/lib/theme-utils.ts` with new CSS variables

### Phase 2.2: Animation & Motion System

**What was built:** Motion primitives, page animations, micro-interactions, loading skeletons.

#### Motion Primitives
1. Created `storefront/src/components/motion-primitives.tsx`:
   - `FadeIn` — opacity 0→1 + translateY(20px→0), configurable delay
   - `StaggerChildren` — wraps children with staggered delays (50-80ms each)
   - `SlideIn` — slide from left/right/bottom with configurable distance
   - `ScaleIn` — scale 0.95→1 with opacity
   - `ScrollReveal` — triggers animation when element enters viewport (IntersectionObserver + motion)

#### Page Animations
2. Modified storefront pages to use motion primitives:
   - Homepage: `FadeIn` on each block with stagger
   - Product listing: `StaggerChildren` on product grid cards
   - Product detail: image `ScaleIn`, details `SlideIn`, reviews `ScrollReveal`
   - Categories: `StaggerChildren` on grid
   - Cart: `FadeIn` on items
   - Checkout success: celebration animation + `FadeIn`

#### Micro-Interactions
3. Modified `storefront/src/components/add-to-cart.tsx`:
   - Button: scale pulse on click (0.95→1.05→1), success checkmark animation
   - Cart badge: bounce animation on count change
4. Modified `storefront/src/components/mobile-menu.tsx`:
   - Spring-based physics for drawer animation
   - Staggered nav item entrance

#### Dashboard Motion
5. Created `dashboard/src/components/motion-wrappers.tsx`:
   - FadeIn and StaggerChildren for dashboard pages
   - Animated counter for KPI cards (count up from 0)
6. Applied staggered entrances to platform home, store overview, analytics pages

### Phase 2.3: Storefront Visual Upgrade

**What was built:** Product badges, recently viewed, enhanced product cards.

1. Enhanced product cards with theme-aware styling:
   - "New" badge for products created within 7 days (theme accent color)
   - "Sale" badge when `compare_at_price` exists
   - Image hover zoom (scale 1.05) with overflow-hidden
   - Price styled with theme primary color

2. Created `storefront/src/components/recently-viewed.tsx`:
   - Stores last 8 viewed product slugs in localStorage
   - Horizontal scroll row below product detail
   - Fetches product data from public API

3. Created `storefront/src/components/animated-product-grid.tsx`:
   - StaggerChildren wrapper around product grid
   - Consistent animation across all product listing pages

### Phase 2.4: Dashboard Enhancements

**What was built:** KPI dashboards, command palette, notification badges, enhanced analytics.

#### Store Overview KPI Dashboard
1. Rewrote `dashboard/src/app/stores/[id]/page.tsx`:
   - 4 KPI metric cards: Total Revenue, Total Orders, Total Products, Conversion Rate
   - Animated count-up values
   - Recent orders table (last 5 orders with status badges)
   - Quick actions: "Add Product", "View Storefront", "Manage Theme"
   - Low-stock inventory alerts integration

#### Platform Home Dashboard
2. Rewrote `dashboard/src/app/page.tsx`:
   - Aggregate metrics across all stores
   - Store cards with mini KPI row per store
   - Staggered card entrance animation

#### Command Palette
3. Created `dashboard/src/components/command-palette.tsx`:
   - Trigger: `Ctrl+K` / `Cmd+K`
   - Modal with search input
   - Sections: Pages, Actions, Recent
   - Fuzzy search filtering
   - Keyboard navigation (up/down, enter)
   - Escape to close (handler on input `onKeyDown`)
4. Modified `dashboard/src/components/dashboard-shell.tsx`:
   - Added global keyboard listener for `Ctrl+K`
   - Rendered `<CommandPalette />` at shell level

#### Notification Badges
5. Modified `dashboard/src/components/sidebar.tsx`:
   - Fetch unread notification count on mount
   - Red badge bubble on "Notifications" nav item
   - Pending order count badge on "Orders" nav item

#### Enhanced Analytics
6. Modified `dashboard/src/app/stores/[id]/analytics/page.tsx`:
   - Customer metrics section
   - Animated count-up on metric cards
   - Enhanced chart visualizations

### Phase 2.5: Data & Quality-of-Life Features

**What was built:** CSV export, order notes, inventory alerts, seed script updates.

#### CSV Export
1. Created `backend/app/services/export_service.py` — CSV generation using Python `csv` module, streaming response
2. Created `backend/app/api/exports.py` — 3 export endpoints (orders, products, customers)
3. Added "Export CSV" button to dashboard orders and products list pages

#### Order Notes
4. Added `notes: Text | None` field to Order model
5. New Alembic migration for order notes field
6. Updated order schemas with `notes` field
7. Modified order detail page with "Internal Notes" textarea (auto-save on blur, "Saved" confirmation)

#### Inventory Alerts
8. Created `dashboard/src/components/inventory-alerts.tsx`:
   - Fetches products with `inventory_count < 5`
   - Renders warning cards: "Low stock: {product} — only {n} left"
   - Integrated into store overview page

#### Seed Script Updates
9. Updated `scripts/seed.ts`:
   - Added demo data for new block types (testimonials, countdown, trust badges)
   - Added low-stock products for inventory alert demos
   - Added order notes to some demo orders

### Phase 2 Polish E2E Tests
10. Created `e2e/tests/dashboard/phase2-polish.spec.ts` — 14 tests covering:
    - Platform Home Dashboard (2 tests: store cards, aggregate metrics)
    - Store Overview KPI Dashboard (3 tests: KPI cards, recent orders, quick actions)
    - Order Notes (2 tests: internal notes display, auto-save persistence)
    - CSV Export (2 tests: orders page button, products page button)
    - Command Palette (3 tests: Ctrl+K open, navigation options, Escape close)
    - Inventory Alerts (2 tests: low stock display, no alerts for sufficient stock)

### Phase 2 Polish Verification
- `python -m pytest tests/ -x` — 329 backend tests pass
- `npm run build` (dashboard) — 34 pages compile cleanly
- `npm run build` (storefront) — 18 pages compile cleanly
- `npx playwright test` — 187+ e2e tests pass (24 spec files)

---

## Summary of Platform State

### Architecture Metrics

| Component | Count |
|-----------|-------|
| Backend API routers | 36 |
| Database models | 22 |
| Database tables | ~37 |
| Service files | 30 |
| Schema files | 27 |
| Alembic migrations | 13 |
| Backend tests | 329+ (29 files) |
| E2E tests | 187+ (24 spec files) |
| Dashboard pages | 34 |
| Storefront pages | 18 |
| Dashboard components | 10 |
| Storefront components | 13 |
| Block types | 13 |
| Preset themes | 11 |

### Next Phase: Automation & AI (A1-A8)

The next phase will be built in a separate `automation/` service directory with its own FastAPI, Celery, and Alembic setup. It communicates with the backend via HTTP API only (no shared imports). Features planned:

- A1: Product Research Automation
- A2: AI-Powered Product Import
- A3: SEO Automation
- A4: Email Marketing
- A5: Competitor Monitoring
- A6: Social Media Automation
- A7: Ad Campaign Management
- A8: AI Customer Chatbot
