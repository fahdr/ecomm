# Implementation Steps

Step-by-step implementation guide for each feature in the dropshipping platform.
Features are ordered by dependency and must be completed sequentially.

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
4. Fixed `alembic/env.py` — added `import app.models` so all models register on `Base.metadata` for autogenerate
5. Created `app/schemas/store.py` — CreateStoreRequest, UpdateStoreRequest (partial), StoreResponse
6. Created `app/services/store_service.py` — create_store, list_stores (excludes deleted), get_store (ownership check), update_store (with slug regen), delete_store (soft-delete)
7. Created `app/api/stores.py` — store router with POST, GET (list), GET/{id}, PATCH/{id}, DELETE/{id}
8. Registered store router in `app/main.py`, imported Store in `app/models/__init__.py`
9. Created `tests/test_stores.py` — 20 tests covering CRUD, slug uniqueness, auth, validation, soft-delete, and tenant isolation (4 cross-user tests)

### Frontend steps completed
1. Installed shadcn/ui components: select, textarea, badge, dialog
2. Built store list page at `dashboard/src/app/stores/page.tsx` — card grid with status badges, empty state, "Create Store" button
3. Built create store page at `dashboard/src/app/stores/new/page.tsx` — form with name, niche dropdown (11 categories), description textarea
4. Built store settings page at `dashboard/src/app/stores/[id]/page.tsx` — edit form with all fields, status toggle, delete button with confirmation dialog
5. Updated dashboard home page with "Stores" nav link and "Go to Stores" CTA button

### Verification
- `pytest` — 36 tests pass (16 auth + 1 health + 20 stores - 1 duplicate = 36)
- `npm run build` — compiles without errors, all routes detected
- CRUD operations: create → list → get → update → soft-delete all working
- Tenant isolation: user A cannot see/edit/delete user B's stores

---

## Feature 4: Storefront (Public-Facing Store)

**Status:** Complete

### What was built
Public-facing storefront that resolves stores by slug and renders store-branded pages with dynamic SEO metadata. No authentication required — stores are accessed via their slug.

### Backend steps completed
1. Created `app/schemas/public.py` — `PublicStoreResponse` schema (excludes `user_id` for security)
2. Created `app/api/public.py` — public router with `GET /api/v1/public/stores/{slug}` (only returns active stores)
3. Registered public router in `app/main.py` under `/api/v1` prefix
4. Created `tests/test_public.py` — 6 tests: slug lookup, user_id exclusion, unknown slug 404, paused store 404, deleted store 404, no auth required

### Frontend steps completed
1. Created `storefront/src/lib/types.ts` — TypeScript types mirroring backend public schemas
2. Created `storefront/src/lib/store.ts` — `resolveSlug()` (query param for local dev, subdomain for prod) + `fetchStore()` API call
3. Created `storefront/src/middleware.ts` — extracts store slug on every request, forwards via `x-store-slug` header
4. Created `storefront/src/contexts/store-context.tsx` — `StoreProvider` + `useStore()` hook for client components
5. Built storefront layout (`storefront/src/app/layout.tsx`) — dynamic header with store name/niche, footer with copyright, `generateMetadata()` for SEO
6. Built homepage (`storefront/src/app/page.tsx`) — hero section with store name/description/niche badge, product grid placeholder (4 "Coming soon" cards)
7. Built 404 page (`storefront/src/app/not-found.tsx`) — "Store not found" with explanation text
8. Dynamic SEO metadata: `<title>` from store name (with template), `<meta description>`, Open Graph tags

### Verification
- `pytest` — 42 tests pass (16 auth + 1 health + 6 public + 20 stores - 1 = 42)
- `npm run build` — compiles without errors, routes: `/` (dynamic), `/_not-found`
- Local dev: `localhost:3001?store=my-slug` resolves store and renders branded page
- Missing/invalid slug: shows 404 "Store not found" page
- Public API: no auth required, `user_id` never exposed

---

## Feature 5: Product Management (Manual CRUD)

**Status:** Not started

### Backend steps
1. Create `app/models/product.py` — `Product` model: id, store_id (FK), title, slug, description, price, compare_at_price, cost, images (JSON array), status (draft/active/archived), seo_title, seo_description, created_at, updated_at
2. Create `app/models/product_variant.py` — `ProductVariant` model: id, product_id (FK), name, sku, price, inventory_count
3. Generate and apply Alembic migration
4. Create `app/schemas/product.py` — Pydantic schemas: CreateProduct, UpdateProduct, ProductResponse, VariantRequest, VariantResponse
5. Create `app/services/product_service.py` — CRUD scoped to store:
   - `create_product(db, store_id, data)` — auto-generate slug from title
   - `list_products(db, store_id, page, per_page, search, status_filter)` — paginated
   - `get_product(db, store_id, product_id)`
   - `update_product(db, store_id, product_id, data)`
   - `delete_product(db, store_id, product_id)` — soft-delete (set archived)
6. Create `app/api/products.py` — product router (all require auth + store ownership):
   - `POST /api/v1/stores/{store_id}/products`
   - `GET /api/v1/stores/{store_id}/products` — with `?page=&per_page=&search=&status=`
   - `GET /api/v1/stores/{store_id}/products/{product_id}`
   - `PATCH /api/v1/stores/{store_id}/products/{product_id}`
   - `DELETE /api/v1/stores/{store_id}/products/{product_id}`
7. Create image upload endpoint: `POST /api/v1/stores/{store_id}/products/upload` — save to local filesystem (`/uploads/`), return URL
8. Add public product endpoints to `app/api/public.py`:
   - `GET /api/v1/public/stores/{slug}/products` — paginated list (active only)
   - `GET /api/v1/public/stores/{slug}/products/{product_slug}` — single product detail
9. Register product router in `app/main.py`
10. Write `tests/test_products.py` — CRUD, pagination, search, store scoping, public listing

### Frontend steps (Dashboard)
1. Build product form component (`dashboard/src/components/features/product-form.tsx`) — reusable for create and edit
2. Build product list page (`dashboard/src/app/stores/[id]/products/page.tsx`) — DataTable with search, status filter, pagination
3. Build product create page (`dashboard/src/app/stores/[id]/products/new/page.tsx`)
4. Build product edit page (`dashboard/src/app/stores/[id]/products/[productId]/page.tsx`)
5. Build image uploader component (`dashboard/src/components/features/image-uploader.tsx`)

### Frontend steps (Storefront)
1. Build product grid component (`storefront/src/components/product-grid.tsx`)
2. Build product listing page (`storefront/src/app/products/page.tsx`) — grid with pagination
3. Build product detail page (`storefront/src/app/products/[slug]/page.tsx`) — image gallery, description, variants, price

---

## Feature 6: Shopping Cart & Customer Checkout

**Status:** Not started

### Backend steps
1. Create `app/models/order.py` — `Order` model: id, store_id, customer_email, items (JSON), total, status (pending/paid/shipped/delivered/cancelled), stripe_session_id, created_at
2. Create `app/models/order_item.py` — `OrderItem` model: id, order_id, product_id, variant_id, quantity, unit_price
3. Generate and apply Alembic migration
4. Create `app/services/stripe_service.py` — Stripe Checkout integration:
   - `create_checkout_session(store, cart_items)` — create Stripe session, return URL
   - `handle_checkout_completed(event)` — create order from webhook payload
5. Create `app/api/public.py` additions:
   - `POST /api/v1/public/stores/{slug}/checkout` — validate cart, create Stripe Checkout session
6. Create `app/api/webhooks.py`:
   - `POST /api/v1/webhooks/stripe` — verify signature, handle `checkout.session.completed`
7. Create `app/services/order_service.py` — create order from webhook, list orders for store owner
8. Create `app/api/orders.py` (auth required):
   - `GET /api/v1/stores/{store_id}/orders` — paginated list
   - `GET /api/v1/stores/{store_id}/orders/{order_id}` — detail
9. Register routers in `app/main.py`
10. Write `tests/test_orders.py` and `tests/test_checkout.py`

### Frontend steps (Storefront)
1. Create cart context/hook (`storefront/src/contexts/cart-context.tsx`) — localStorage persistence, add/remove/update quantity
2. Add "Add to Cart" button to product detail page
3. Build cart drawer or page (`storefront/src/app/cart/page.tsx`) — item list, quantities, total
4. Build checkout redirect — call backend to create Stripe session, redirect to Stripe
5. Build order confirmation page (`storefront/src/app/checkout/success/page.tsx`)

### Frontend steps (Dashboard)
1. Build orders list page (`dashboard/src/app/stores/[id]/orders/page.tsx`)
2. Build order detail page (`dashboard/src/app/stores/[id]/orders/[orderId]/page.tsx`)

---

## Feature 7: Stripe Subscriptions (SaaS Billing)

**Status:** Not started

### Backend steps
1. Create `app/models/subscription.py` — `Subscription` model: id, user_id, stripe_subscription_id, stripe_customer_id, plan (starter/growth/pro), status, current_period_start, current_period_end, trial_end
2. Generate and apply Alembic migration
3. Extend `app/services/stripe_service.py`:
   - `create_subscription_checkout(user, plan)` — Stripe Checkout in subscription mode
   - `create_portal_session(user)` — Stripe Customer Portal for self-service
   - `sync_subscription(stripe_event)` — update local DB from webhook
4. Add webhook handlers in `app/api/webhooks.py` for: `customer.subscription.created`, `.updated`, `.deleted`, `invoice.payment_failed`
5. Create plan enforcement middleware (`app/api/deps.py`):
   - `get_current_plan(user)` — returns plan limits (max stores, max products)
   - Check limits before store/product creation
6. Create `app/api/subscriptions.py`:
   - `POST /api/v1/subscriptions/checkout` — create subscription checkout
   - `POST /api/v1/subscriptions/portal` — create portal session
   - `GET /api/v1/subscriptions/current` — get active subscription
7. Write `tests/test_subscriptions.py`

### Frontend steps
1. Build pricing page (`dashboard/src/app/pricing/page.tsx`) — 3-tier comparison table
2. Build billing page (`dashboard/src/app/settings/billing/page.tsx`) — current plan, usage, manage link
3. Add plan limit enforcement in UI — disable "Create Store" if at limit, show upgrade prompt
4. Integrate Stripe Customer Portal redirect from billing page

---

## Feature 8: Product Research Automation

**Status:** Not started

### Backend steps
1. Create `app/models/watchlist_item.py` — `WatchlistItem` model: id, store_id, source, source_url, title, image_url, price, score, ai_analysis, status (new/imported/dismissed), found_at
2. Generate and apply Alembic migration
3. Create `app/services/research/aliexpress.py` — AliExpress affiliate API client: search by niche keywords, parse results
4. Create `app/services/research/reddit.py` — Reddit via PRAW: search trending product mentions in relevant subreddits
5. Create `app/services/research/scoring.py` — weighted scoring algorithm: trend velocity, price margin potential, competition level, social mentions
6. Create `app/services/ai_service.py` — Claude API integration:
   - `analyze_products(products)` — send top 20 to Claude for market analysis, demand prediction, risk assessment
7. Create `app/tasks/research_tasks.py`:
   - `daily_product_research(store_id)` — orchestrate: fetch from sources → score → AI analysis → save to watchlist
8. Configure Celery Beat schedule in `celery_app.py` — run daily for each active store
9. Create `app/api/research.py`:
   - `GET /api/v1/stores/{store_id}/research` — list research results (paginated, filterable)
   - `POST /api/v1/stores/{store_id}/research/{item_id}/dismiss` — mark as dismissed
10. Write `tests/test_research.py` — test scoring algorithm, task execution (mock external APIs)

### Frontend steps
1. Build research results page (`dashboard/src/app/stores/[id]/research/page.tsx`) — table with scores, AI reasoning, source link, import button
2. Build watchlist page (`dashboard/src/app/stores/[id]/watchlist/page.tsx`) — saved/bookmarked items
3. Build research settings (`dashboard/src/app/stores/[id]/settings/research/page.tsx`) — niche keywords, frequency

---

## Feature 9: Automated Product Import + AI Content

**Status:** Not started

### Backend steps
1. Create `app/services/import_service.py` — orchestrator:
   - Download images from source URL
   - Call AI for title, description, SEO metadata
   - Calculate pricing (markup %, psychological pricing)
   - Create product as draft
2. Create `app/services/ai_content_service.py` — Claude API prompts:
   - `generate_product_title(source_title, niche)` — SEO-optimized title
   - `generate_product_description(source_data)` — compelling product copy
   - `generate_seo_metadata(product)` — meta title, meta description, keywords
3. Create `app/services/image_service.py` — download, optimize (WebP conversion, resize), save to storage
4. Create `app/utils/pricing.py` — markup calculation, psychological pricing (e.g. $29.97 → $29.99)
5. Create `app/tasks/import_tasks.py`:
   - `import_product(store_id, watchlist_item_id)` — Celery chain: download → AI content → optimize images → create draft product
6. Create API endpoint: `POST /api/v1/stores/{store_id}/products/import` — accepts watchlist_item_id, kicks off Celery task
7. Write `tests/test_import.py`

### Frontend steps
1. Add "Import" button to research results table — triggers import API call
2. Build import progress indicator (poll task status or use WebSocket)
3. Build review page — show AI-generated draft, allow edits before publishing

---

## Feature 10: SEO Automation

**Status:** Not started

### Backend steps
1. Create `app/models/blog_post.py` — `BlogPost` model: id, store_id, title, slug, content, seo_title, seo_description, status (draft/published), published_at
2. Generate and apply Alembic migration
3. Create `app/services/seo_service.py`:
   - `generate_sitemap(store)` — build XML sitemap from products + blog posts
   - `generate_schema_markup(product)` — JSON-LD Product schema
   - `generate_blog_post(store, keyword)` — Claude API for SEO blog content
4. Create `app/tasks/seo_tasks.py`:
   - `weekly_seo_optimization(store_id)` — generate blog posts for keyword gaps
5. Create `app/api/public.py` additions:
   - `GET /api/v1/public/stores/{slug}/blog` — list published posts
   - `GET /api/v1/public/stores/{slug}/blog/{post_slug}` — single post
6. Write `tests/test_seo.py`

### Frontend steps (Storefront)
1. Add `sitemap.xml` route (`storefront/src/app/sitemap.ts`)
2. Add JSON-LD script tags to product detail pages
3. Build blog listing page (`storefront/src/app/blog/page.tsx`)
4. Build blog detail page (`storefront/src/app/blog/[slug]/page.tsx`)

### Frontend steps (Dashboard)
1. Build SEO overview page (`dashboard/src/app/stores/[id]/seo/page.tsx`) — scores, suggestions, blog post list

---

## Feature 11: Email Automation

**Status:** Not started

### Backend steps
1. Create `app/models/email_flow.py` — `EmailFlow` model: id, store_id, trigger (welcome/abandoned_cart/post_purchase), enabled, delays (JSON), template_id
2. Create `app/models/email_event.py` — `EmailEvent` model: id, flow_id, recipient_email, status (sent/failed/opened), sent_at
3. Generate and apply Alembic migration
4. Create `app/services/email_service.py` — SendGrid SDK integration:
   - `send_email(to, subject, template, context)` — render Jinja2 template, send via SendGrid
5. Create email templates in `backend/templates/` — welcome, abandoned cart (1hr, 24hr, 72hr), order confirmation, daily research report
6. Create `app/tasks/email_tasks.py`:
   - `send_welcome_email(customer_email, store_id)`
   - `check_abandoned_carts(store_id)` — find carts older than thresholds, send reminders
   - `send_order_confirmation(order_id)`
   - `send_daily_research_report(user_id)`
7. Create `app/api/email_flows.py` — CRUD for email flow configuration
8. Write `tests/test_email.py`

### Frontend steps
1. Build email flow configuration page (`dashboard/src/app/stores/[id]/settings/email/page.tsx`) — toggle flows on/off, set delays

---

## Feature 12: Analytics Dashboard

**Status:** Not started

### Backend steps
1. Create `app/services/analytics_service.py` — aggregate queries:
   - `get_revenue_over_time(store_id, date_range)` — daily/weekly revenue
   - `get_order_stats(store_id, date_range)` — count, average value
   - `get_product_performance(store_id, date_range)` — views, orders, conversion rate per product
   - `get_visitor_stats(store_id, date_range)` — page views over time
2. Add Redis caching for expensive queries (TTL: 5 minutes)
3. Create `app/api/analytics.py`:
   - `GET /api/v1/stores/{store_id}/analytics/overview` — revenue, orders, visitors summary
   - `GET /api/v1/stores/{store_id}/analytics/products` — product performance table
   - `GET /api/v1/stores/{store_id}/analytics/revenue` — revenue chart data
4. Create event tracking endpoint: `POST /api/v1/public/stores/{slug}/events` — track page_view, add_to_cart, purchase
5. Write `tests/test_analytics.py`

### Frontend steps (Storefront)
1. Add event tracking calls on: page load (page_view), add to cart button (add_to_cart), checkout success (purchase)

### Frontend steps (Dashboard)
1. Install Recharts: `npm install recharts`
2. Build analytics overview page (`dashboard/src/app/stores/[id]/analytics/page.tsx`) — summary cards + revenue line chart
3. Build product performance table component
4. Build date range picker component (7d, 30d, 90d, custom)

---

## Feature 13: Kubernetes Deployment & CI/CD

**Status:** Not started

### Infrastructure steps
1. Create production Dockerfiles (multi-stage builds):
   - `backend/Dockerfile` — Python 3.12 slim, pip install, uvicorn
   - `dashboard/Dockerfile` — Node 20 alpine, npm build, standalone output
   - `storefront/Dockerfile` — Node 20 alpine, npm build, standalone output
2. Create `k8s/base/` — namespace (`dropshipping`), secrets, configmaps
3. Create `k8s/base/postgres.yaml` — StatefulSet + PVC + Service (or connect to managed DB)
4. Create `k8s/base/redis.yaml` — Deployment + Service
5. Create `k8s/backend/` — Deployment (3 replicas), Service (ClusterIP), Ingress (`api.platform.com`)
6. Create `k8s/celery/worker-deployment.yaml` — Deployment (2 replicas)
7. Create `k8s/celery/beat-deployment.yaml` — Deployment (1 replica, singleton)
8. Create `k8s/celery/flower-deployment.yaml` — Deployment + Ingress
9. Create `k8s/dashboard/` — Deployment (2 replicas), Service, Ingress (`dashboard.platform.com`)
10. Create `k8s/storefront/` — Deployment (2 replicas), Service, Ingress with wildcard subdomain (`*.platform.com`)
11. Create HPA for backend + storefront (min 2, max 10, CPU target 70%)
12. Create `k8s/kustomization.yaml` — ties all resources together
13. Set up cert-manager + Let's Encrypt for TLS
14. Create `.github/workflows/backend.yml` — on push to main: run pytest → build Docker image → push to registry → kubectl apply
15. Create `.github/workflows/dashboard.yml` — build → push → deploy
16. Create `.github/workflows/storefront.yml` — build → push → deploy

### Verification
- All pods running in `dropshipping` namespace
- Backend accessible at `api.platform.com`
- Dashboard accessible at `dashboard.platform.com`
- Storefront accessible at `*.platform.com`
- TLS certificates issued
- CI/CD deploys on push to main
