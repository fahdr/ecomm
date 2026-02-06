# Feature Backlog (Agile)

Each feature is a self-contained deliverable. We build one at a time, top to bottom.
Features are ordered by dependency — each builds on what came before.
Local dev via devcontainer (Docker Compose). K8s deployment at the end.

**Legend:** `[P]` = Python backend, `[N]` = Next.js frontend, `[K]` = Kubernetes/infra

---

## Feature 1: Project Scaffolding & Local Dev Environment
**Priority:** Must have | **Estimated effort:** Small

### What we're building
The foundational project structure and runnable apps inside the devcontainer.

### Acceptance criteria
- [ ] Devcontainer starts: PostgreSQL + Redis healthy, Python + Node.js available
- [ ] Backend: FastAPI app returns `{"status": "ok"}` at `localhost:8000/health`
- [ ] Dashboard: Next.js app loads at `localhost:3000`
- [ ] Storefront: Next.js app loads at `localhost:3001`
- [ ] Celery worker connects to Redis and logs "ready"
- [ ] Alembic is initialized, first migration runs (creates empty DB)
- [ ] pytest runs with 1 passing health-check test

### Tasks
- [P] Init FastAPI project with pyproject.toml
- [P] Create config module (pydantic-settings, reads env vars from devcontainer)
- [P] Set up SQLAlchemy async engine + session factory
- [P] Initialize Alembic with async support
- [P] Set up Celery app with Redis broker
- [P] Write `/health` endpoint + first pytest
- [N] Init Next.js dashboard app with Shadcn/ui + Tailwind
- [N] Init Next.js storefront app with Tailwind
- [N] Create API client utility (fetch wrapper pointing to `localhost:8000`)

---

## Feature 2: User Authentication
**Priority:** Must have | **Estimated effort:** Medium

### What we're building
Registration, login, JWT access/refresh tokens, password reset. Backend API + dashboard UI.

### Acceptance criteria
- [ ] `POST /api/v1/auth/register` — create user, return tokens
- [ ] `POST /api/v1/auth/login` — validate credentials, return tokens
- [ ] `POST /api/v1/auth/refresh` — rotate refresh token, return new access token
- [ ] `POST /api/v1/auth/forgot-password` — send reset email (stubbed for now)
- [ ] `GET /api/v1/auth/me` — return current user (requires valid JWT)
- [ ] Passwords hashed with bcrypt (passlib)
- [ ] Access token expires in 15 min, refresh token in 7 days
- [ ] Dashboard: registration page, login page, logout
- [ ] Dashboard: protected routes redirect to login if unauthenticated
- [ ] Alembic migration for `users` table

### Tasks
- [P] Create `User` SQLAlchemy model (id, email, hashed_password, created_at)
- [P] Create Alembic migration
- [P] Create Pydantic schemas (RegisterRequest, LoginRequest, TokenResponse, UserResponse)
- [P] Implement auth_service (register, login, verify_token, refresh)
- [P] Implement auth router (register, login, refresh, me)
- [P] Create `get_current_user` FastAPI dependency
- [P] Write tests for all auth endpoints
- [N] Install and configure Shadcn/ui components (form, input, button, card)
- [N] Build registration page
- [N] Build login page
- [N] Create auth context/hook (store JWT, refresh logic)
- [N] Add protected route middleware
- [N] Add logout functionality

---

## Feature 3: Store Creation (Backend + Dashboard)
**Priority:** Must have | **Estimated effort:** Medium

### What we're building
Users can create a store from the dashboard. Store gets a slug for subdomain routing. Basic CRUD.

### Acceptance criteria
- [ ] `POST /api/v1/stores` — create store (name, niche, description)
- [ ] `GET /api/v1/stores` — list user's stores
- [ ] `GET /api/v1/stores/{id}` — get store details
- [ ] `PATCH /api/v1/stores/{id}` — update store settings
- [ ] `DELETE /api/v1/stores/{id}` — soft-delete store
- [ ] Store slug auto-generated from name (unique)
- [ ] Dashboard: "Create Store" form with niche picker
- [ ] Dashboard: store list page showing all user's stores
- [ ] Dashboard: store detail/settings page
- [ ] Tenant isolation: users can only see their own stores
- [ ] Alembic migration for `stores` table

### Tasks
- [P] Create `Store` model (id, user_id, name, slug, niche, description, status, created_at)
- [P] Alembic migration
- [P] Pydantic schemas (CreateStore, UpdateStore, StoreResponse)
- [P] Store service (create, list, get, update, delete)
- [P] Store router with tenant_middleware dependency
- [P] Slug generation utility (name → unique slug)
- [P] Tests
- [N] Build "Create Store" wizard page (name, niche, description)
- [N] Build store list page (card grid)
- [N] Build store settings page
- [N] Add sidebar navigation (stores dropdown)

---

## Feature 4: Storefront (Public-Facing Store)
**Priority:** Must have | **Estimated effort:** Medium

### What we're building
The customer-facing store. A single Next.js app that resolves the store slug and renders it.
Locally, test via `localhost:3001?store=my-store-slug` (subdomain routing added in K8s later).

### Acceptance criteria
- [ ] Storefront resolves store from query param locally (subdomain in production)
- [ ] Homepage shows store name, description, and (empty) product grid
- [ ] 404 page for unknown store slugs
- [ ] Store data fetched server-side (SSR) from backend API
- [ ] Basic layout: header (store name), product grid, footer
- [ ] SEO: correct `<title>`, `<meta description>`, Open Graph tags
- [ ] API endpoint: `GET /api/v1/public/stores/{slug}` (no auth required)

### Tasks
- [P] Create public store endpoint (by slug, no auth)
- [N] Create store resolution logic (query param locally, subdomain in prod)
- [N] Create store context (resolved store data available to all pages)
- [N] Build storefront layout (header, footer, nav)
- [N] Build homepage (hero section, product grid placeholder)
- [N] Build 404 / "store not found" page
- [N] SEO: dynamic metadata from store data

---

## Feature 5: Product Management (Manual CRUD)
**Priority:** Must have | **Estimated effort:** Medium

### What we're building
Store owners can manually add, edit, and delete products. Products display on the storefront.

### Acceptance criteria
- [ ] `POST /api/v1/stores/{store_id}/products` — create product
- [ ] `GET /api/v1/stores/{store_id}/products` — list with pagination, search, filter
- [ ] `PATCH /api/v1/stores/{store_id}/products/{id}` — update
- [ ] `DELETE /api/v1/stores/{store_id}/products/{id}` — soft-delete
- [ ] Image upload to local filesystem (S3 later)
- [ ] Dashboard: product creation form (title, description, price, images, variants)
- [ ] Dashboard: product list with search and status filter
- [ ] Dashboard: product edit page
- [ ] Storefront: product listing page (grid with pagination)
- [ ] Storefront: product detail page (images, description, price, variants)
- [ ] Public API: `GET /api/v1/public/stores/{slug}/products`

### Tasks
- [P] Create `Product` model (id, store_id, title, slug, description, price, compare_at_price, cost, images, status, seo fields)
- [P] Create `ProductVariant` model (id, product_id, name, sku, price, inventory)
- [P] Alembic migration
- [P] Pydantic schemas
- [P] Product service + router (CRUD, scoped to store)
- [P] Image upload endpoint (local storage for now, swap to S3 later)
- [P] Public product endpoints (list + detail by slug)
- [P] Tests
- [N] Dashboard: product form component (reused for create/edit)
- [N] Dashboard: product list page with DataTable
- [N] Dashboard: image uploader component
- [N] Storefront: product grid component
- [N] Storefront: product listing page
- [N] Storefront: product detail page (image gallery, variant selector)

---

## Feature 6: Shopping Cart & Customer Checkout
**Priority:** Must have | **Estimated effort:** Medium

### What we're building
Store customers can add products to cart and checkout with Stripe.

### Acceptance criteria
- [ ] Cart stored client-side (localStorage) with API validation
- [ ] Add to cart, update quantity, remove item
- [ ] Cart drawer/page showing items and total
- [ ] Stripe Checkout session created from cart
- [ ] Successful payment creates an `Order` in the database
- [ ] Order confirmation page
- [ ] Webhook: `checkout.session.completed` → create order
- [ ] Store owner sees orders in dashboard
- [ ] Dashboard: order list page

### Tasks
- [P] Create `Order` model (id, store_id, customer_email, items, total, status, stripe_session_id)
- [P] Create `OrderItem` model
- [P] Alembic migration
- [P] `POST /api/v1/public/stores/{slug}/checkout` — create Stripe session
- [P] `POST /api/v1/webhooks/stripe` — handle checkout.session.completed
- [P] Order service (create from webhook, list for store owner)
- [P] Order router (store-scoped list + detail)
- [P] Tests
- [N] Storefront: cart context/hook (localStorage + state)
- [N] Storefront: "Add to Cart" button on product pages
- [N] Storefront: cart drawer or page
- [N] Storefront: checkout redirect (Stripe Checkout)
- [N] Storefront: order confirmation page
- [N] Dashboard: orders list page
- [N] Dashboard: order detail page

---

## Feature 7: Stripe Subscriptions (SaaS Billing)
**Priority:** Must have | **Estimated effort:** Medium

### What we're building
Platform billing. Users pick a plan (Starter/Growth/Pro) and subscribe via Stripe.

### Acceptance criteria
- [ ] Pricing page with 3 tiers
- [ ] Stripe Checkout for subscriptions
- [ ] Webhook handles: subscription created, updated, canceled, payment failed
- [ ] User's plan stored in DB, enforced on API (store limits, product limits)
- [ ] Dashboard: billing page (current plan, usage, manage subscription)
- [ ] Stripe Customer Portal for self-service plan changes
- [ ] Free trial support (14 days)

### Tasks
- [P] Create `Subscription` model (id, user_id, stripe_subscription_id, plan, status, current_period_end)
- [P] Alembic migration
- [P] Stripe service (create checkout session, create portal session, sync subscription)
- [P] Webhook handler for subscription events
- [P] Plan enforcement middleware (check user's plan limits before store/product creation)
- [P] Tests
- [N] Dashboard: pricing page with plan comparison
- [N] Dashboard: billing page (current plan, upgrade/downgrade, cancel)
- [N] Dashboard: integrate Stripe Customer Portal redirect
- [N] Dashboard: enforce plan limits in UI (disable features, show upgrade prompts)

---

## Feature 8: Product Research Automation
**Priority:** High | **Estimated effort:** Large

### What we're building
Automated daily product research: pull trends from AliExpress, Reddit, Google Trends. Score products with AI. Present recommendations to users.

### Acceptance criteria
- [ ] Celery Beat triggers daily research for each active store
- [ ] Data pulled from at least 2 sources (AliExpress API + Reddit via PRAW)
- [ ] Products scored with weighted algorithm
- [ ] Top 20 products analyzed by Claude API
- [ ] Results saved to `WatchlistItem` table
- [ ] Dashboard: "Product Research" page showing daily results
- [ ] Dashboard: one-click import from research results
- [ ] Daily email report (summary of findings)

### Tasks
- [P] Create `WatchlistItem` model
- [P] AliExpress research service (affiliate API)
- [P] Reddit research service (PRAW)
- [P] Google Trends service (pytrends) — optional, add if time allows
- [P] Product scoring algorithm
- [P] AI analysis service (Claude API)
- [P] Celery task: daily_product_research (per store)
- [P] Celery Beat schedule config
- [P] Research results API endpoints
- [P] Tests
- [N] Dashboard: research results page (table with scores, AI reasoning, import button)
- [N] Dashboard: watchlist page
- [N] Dashboard: research settings (niche keywords, frequency)

---

## Feature 9: Automated Product Import + AI Content
**Priority:** High | **Estimated effort:** Medium

### What we're building
Import a researched product into the store with AI-generated title, description, SEO metadata, and optimized images.

### Acceptance criteria
- [ ] One-click import from research results
- [ ] AI generates: SEO title, product description, meta description, keywords
- [ ] Images downloaded from source, optimized (WebP, resized), uploaded to storage
- [ ] Pricing auto-calculated (configurable markup, psychological pricing)
- [ ] Product created as draft (user reviews before publishing)
- [ ] Celery task handles the full pipeline (retries on failure)

### Tasks
- [P] Import service (orchestrates the full pipeline)
- [P] AI content generation service (Claude API prompts for product copy)
- [P] Image download + optimization service (Pillow)
- [P] Pricing calculation utility
- [P] Celery task: import_product (chain of steps)
- [P] API endpoint: `POST /api/v1/stores/{store_id}/products/import`
- [P] Tests
- [N] Dashboard: import progress indicator
- [N] Dashboard: review imported product before publishing

---

## Feature 10: SEO Automation
**Priority:** Medium | **Estimated effort:** Medium

### What we're building
Automated SEO: sitemaps, schema markup, meta tags, and AI-generated blog posts.

### Acceptance criteria
- [ ] Auto-generated sitemap.xml for each store
- [ ] JSON-LD schema markup on product pages (Product schema)
- [ ] AI-generated blog posts targeting keyword gaps (weekly Celery task)
- [ ] Dashboard: SEO overview page (scores, suggestions)
- [ ] Blog posts display on storefront at `/blog/{slug}`

### Tasks
- [P] Create `BlogPost` model
- [P] Sitemap generation service
- [P] Schema markup generation service
- [P] AI blog post generation (Claude API)
- [P] Celery task: weekly_seo_optimization
- [P] Public blog API endpoints
- [N] Storefront: sitemap.xml route
- [N] Storefront: JSON-LD on product pages
- [N] Storefront: blog listing + detail pages
- [N] Dashboard: SEO overview page

---

## Feature 11: Email Automation
**Priority:** Medium | **Estimated effort:** Medium

### What we're building
Automated email flows: welcome series, abandoned cart, post-purchase. Via SendGrid.

### Acceptance criteria
- [ ] Email service integrated (SendGrid)
- [ ] Welcome email on store customer signup
- [ ] Abandoned cart email (1hr, 24hr, 72hr)
- [ ] Order confirmation email
- [ ] Store owner: daily product research report email
- [ ] Dashboard: email flow configuration page

### Tasks
- [P] Email service (SendGrid SDK, Jinja2 templates)
- [P] Create `EmailFlow` and `EmailEvent` models
- [P] Celery tasks for each email flow
- [P] Abandoned cart detection logic
- [P] API endpoints for email flow CRUD
- [N] Dashboard: email flow builder/configurator

---

## Feature 12: Analytics Dashboard
**Priority:** Medium | **Estimated effort:** Medium

### What we're building
Store performance metrics: revenue, orders, visitors, product performance.

### Acceptance criteria
- [ ] Dashboard: analytics overview (revenue, orders, visitors over time)
- [ ] Dashboard: product performance table (views, orders, conversion rate)
- [ ] Charts (line chart for revenue, bar chart for top products)
- [ ] Date range picker (7d, 30d, 90d, custom)
- [ ] Data aggregated server-side, cached in Redis

### Tasks
- [P] Analytics service (aggregate queries)
- [P] API endpoints (overview, product performance, revenue)
- [P] Redis caching for expensive queries
- [P] Event tracking: page views, add-to-cart, purchases
- [N] Dashboard: analytics overview page
- [N] Dashboard: charts (Recharts)
- [N] Dashboard: date range picker
- [N] Storefront: event tracking (page views, add-to-cart)

---

## Feature 13: Kubernetes Deployment & CI/CD
**Priority:** Must have (but last) | **Estimated effort:** Medium

### What we're building
Deploy the complete platform to the existing K8s cluster. CI/CD pipeline.

### Acceptance criteria
- [ ] All services deploy to K8s namespace `dropshipping`
- [ ] Backend reachable at `api.platform.com`
- [ ] Dashboard reachable at `dashboard.platform.com`
- [ ] Storefront with wildcard subdomain: `*.platform.com`
- [ ] PostgreSQL and Redis running (StatefulSet or managed)
- [ ] Celery worker + beat + Flower running
- [ ] GitHub Actions: push to `main` triggers build → deploy
- [ ] TLS via cert-manager + Let's Encrypt

### Tasks
- [K] Create Dockerfiles for production (multi-stage builds)
- [K] Create namespace, secrets, configmaps
- [K] PostgreSQL StatefulSet + Service (or connect to managed DB)
- [K] Redis Deployment + Service
- [K] Backend Deployment + Service + Ingress
- [K] Celery Worker Deployment
- [K] Celery Beat Deployment (single replica)
- [K] Flower Deployment + Ingress
- [K] Dashboard Deployment + Service + Ingress
- [K] Storefront Deployment + Service + Ingress (wildcard subdomain)
- [K] HPA for backend + storefront
- [K] GitHub Actions: build images, push to registry, kubectl apply

---

## Future Features (Backlog — Not Scheduled)

| Feature                      | Description                                         |
| ---------------------------- | --------------------------------------------------- |
| Custom domains               | Users bring their own domain, auto-SSL via cert-manager |
| Social media automation      | Auto-post new products to Instagram/Facebook        |
| Ad campaign management       | Google Ads + Meta Ads API integration               |
| TikTok trend scraping        | Apify integration for TikTok product discovery      |
| Competitor monitoring        | Scrape competitor stores, find their products        |
| Multi-store management       | Manage multiple stores from unified view             |
| White-label                  | Remove platform branding (Pro/Enterprise)            |
| A/B testing                  | Test product titles, prices, images                  |
| API access                   | Public API for programmatic store management         |
| Referral program             | Users earn credits for referrals                     |
| Mobile app                   | React Native dashboard app                           |

---

## Working Agreement

- **One feature at a time.** Finish and test locally before starting the next.
- **Tests are mandatory** for backend API endpoints.
- **No premature optimization.** Get it working, then improve.
- **Backend first, then frontend.** API is the source of truth.
- **Local dev only** until Feature 13 (K8s deployment).
