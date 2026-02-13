# Feature Backlog (Agile) — Dropshipping Automation Platform

Each feature is a self-contained deliverable. We build one at a time, top to bottom.
Features are ordered by **impact** — most impactful to revenue, conversion, and the platform's automation USP first.
Local dev via devcontainer (Docker Compose). K8s deployment at the end.

> **This is a dropshipping automation SaaS platform**, not a generic ecommerce builder.
> Store owners do NOT hold inventory or handle shipping — suppliers (AliExpress, CJ Dropshipping, etc.)
> ship directly to customers. Our key differentiator is **end-to-end automation**: AI-powered product
> research, auto-import, content generation, SEO, and marketing — enabling users to scale with minimal
> manual intervention.
>
> See [dropshipping-platform-master-plan.md](../dropshipping-platform-master-plan.md) for the full
> business plan, pricing strategy, and implementation roadmap.

> **Two-phase approach:** We build the platform in two phases. **Phase 1** focuses on the core platform —
> all the manual/essential ecommerce features a dropshipping store needs to operate (discounts, categories,
> reviews, fulfillment, analytics, themes, etc.). **Phase 2** adds the automation and AI features that are
> the platform's key differentiator (product research, AI import, SEO automation, email marketing, competitor
> monitoring, social media, ad campaigns, AI shopping assistant). Phase 2 is built on the Automation service
> (`automation/`) and is implemented after Phase 1 is stable and well-tested.

**Legend:** `[P]` = Python backend, `[A]` = Automation service (separate Python/FastAPI service), `[N]` = Next.js frontend, `[K]` = Kubernetes/infra | **Phase 1** = Core platform features (F8-F31), **Phase 2** = Automation & AI features (A1-A8)

> **Note:** Automation features (Product Research, AI Import, SEO, Email Marketing) belong to the **Automation Service** (`automation/`),
> a standalone service that communicates with the core backend via HTTP API.
> It is designed to be extractable as a separate product in the future.
> See [ARCHITECTURE.md](ARCHITECTURE.md) for design principles and separation rules.

---

## Completed Features (F1-F7.5: Core Platform Foundation)

### Feature 1: Project Scaffolding & Local Dev Environment ✅
**Status:** Complete

Foundational project structure and runnable apps inside the devcontainer.
- Devcontainer with PostgreSQL 16 + Redis 7 + Python 3.12 + Node.js 20
- FastAPI backend on port 8000 with `/health` endpoint
- Next.js dashboard on port 3000
- Next.js storefront on port 3001
- Celery worker + Beat scheduler
- Alembic migrations initialized
- pytest passing

---

### Feature 2: User Authentication ✅
**Status:** Complete

Registration, login, JWT access/refresh tokens, password reset stub.
- `POST /api/v1/auth/register`, `login`, `refresh`, `forgot-password`, `GET /me`
- JWT access tokens (15 min) + refresh tokens (7 days)
- Bcrypt password hashing
- Dashboard: login, register pages, protected routes, logout

---

### Feature 3: Store Creation ✅
**Status:** Complete

Store CRUD with slug-based routing and tenant isolation.
- Full CRUD API for stores
- Auto-generated unique slugs
- Dashboard: create store wizard, store list, store settings
- Plan enforcement: store limits per plan

---

### Feature 4: Storefront (Public-Facing Store) ✅
**Status:** Complete

Customer-facing store with SSR and SEO.
- Store resolution from query param (local) / subdomain (prod)
- Homepage, product grid, 404 page
- SEO metadata: title, description, Open Graph tags

---

### Feature 5: Product Management ✅
**Status:** Complete

Manual product CRUD with variants, images, and storefront display.
- Full product API with pagination, search, filtering
- Product variants with SKU, price, inventory
- Image upload to local filesystem
- Dashboard: product list (DataTable), create/edit forms
- Storefront: product grid, detail page with image gallery and variant selector

---

### Feature 6: Shopping Cart & Customer Checkout ✅
**Status:** Complete

Client-side cart with Stripe Checkout integration.
- localStorage cart with API validation
- Stripe Checkout session creation
- Webhook-driven order creation
- Order confirmation page
- Dashboard: order list and detail pages

---

### Feature 7: Stripe Subscriptions (SaaS Billing) ✅
**Status:** Complete

Platform billing with four subscription tiers.
- Free / Starter ($29) / Growth ($79) / Pro ($199) tiers
- Stripe Checkout + Customer Portal
- Webhook handlers for subscription lifecycle
- Plan enforcement middleware
- Dashboard: pricing page, billing page with usage stats
- 14-day free trial for paid plans

---

### Feature 7.5: Storefront Customer Accounts ✅
**Status:** Complete

Per-store customer authentication, order history, and wishlists.
- Customer registration/login (separate from store owner auth)
- Customer profile management
- Order history with detail views
- Wishlist (add/remove/list)
- Dashboard: customer list and detail pages

---

## Phase 1: Core Platform Features ✅

> **Phase 1 scope:** These features build the core dropshipping platform — everything a store owner needs
> to operate a functional, trustworthy, and competitive dropshipping business. This includes product
> organization, supplier management, order fulfillment, analytics, customer tools, store customization,
> and operational infrastructure. All Phase 1 features use the core backend (`backend/`) and frontend
> apps (`dashboard/`, `storefront/`). Phase 2 (Automation & AI) is built after Phase 1 is stable.

**Status:** All Phase 1 features (F8-F30) are implemented, plus the full Polish Plan (Phases A-G) and Phase 2 Polish (5 phases). The platform is now demo-able end-to-end with premium visual polish.

**Current totals:**
- **541 backend tests passing** (41+ test files, including 53 Celery task tests)
- **187+ e2e tests passing** (24 Playwright spec files — empty state + populated data + seed data + phase 2 polish)
- **36 dashboard pages** building cleanly
- **18 storefront pages** building cleanly
- **14 Alembic migrations**, ~38 DB tables
- **11 preset themes**, 13 block types, motion animations throughout
- **20 Celery task functions** across 6 modules (email, webhook, notification, fraud, order, analytics)
- **3 Celery Beat scheduled tasks** (daily analytics, notification cleanup, fulfillment checks)
- Backend API endpoints (FastAPI + SQLAlchemy async)
- Dashboard UI pages (Next.js + Shadcn/ui)
- Storefront UI components (Next.js + Tailwind)
- Backend unit/integration tests (pytest + httpx AsyncClient)
- Alembic migration for all new database tables

### Implementation Summary

| Feature | Backend | Dashboard | Storefront | Tests |
|---------|---------|-----------|------------|-------|
| F8: Discounts | `api/discounts.py`, `services/discount_service.py` | `stores/[id]/discounts/` | Cart integration | `test_discounts.py` + e2e |
| F9: Categories | `api/categories.py`, `services/category_service.py` | `stores/[id]/categories/` | `categories/`, header nav | `test_categories.py` + e2e |
| F10: Suppliers | `api/suppliers.py`, `services/supplier_service.py` | `stores/[id]/suppliers/` | — | `test_suppliers.py` + e2e |
| F11: Email | `services/email_service.py`, templates | `stores/[id]/email/` | — | — |
| F12: Reviews | `api/reviews.py`, `services/review_service.py` | `stores/[id]/reviews/` | `product-reviews.tsx` | `test_reviews.py` + e2e |
| F13: Analytics | `api/analytics.py`, `services/analytics_service.py` | `stores/[id]/analytics/` | — | `test_analytics.py` + e2e |
| F14: Refunds | `api/refunds.py`, `services/refund_service.py` | `stores/[id]/refunds/` | — | `test_refunds.py` + e2e |
| F15: Themes | — | `stores/[id]/themes/` | Dynamic styling | e2e |
| F16: Tax | `api/tax.py`, `services/tax_service.py` | `stores/[id]/tax/` | Cart integration | `test_tax.py` + e2e |
| F17: Search | `api/search.py`, `services/search_service.py` | — | `search/`, `header-search.tsx` | `test_search.py` + e2e |
| F18: Upsells | `api/upsells.py`, `services/upsell_service.py` | `stores/[id]/upsells/` | `product-upsells.tsx` | `test_upsells.py` + e2e |
| F19: Segments | `api/segments.py`, `services/segment_service.py` | `stores/[id]/segments/` | — | `test_segments.py` + e2e |
| F20: Gift Cards | `api/gift_cards.py`, `services/gift_card_service.py` | `stores/[id]/gift-cards/` | — | `test_gift_cards.py` + e2e |
| F21: Currency | `api/currency.py`, `services/currency_service.py` | `stores/[id]/currency/` | — | `test_currency.py` + e2e |
| F22: Domains | `api/domains.py`, `services/domain_service.py` | `stores/[id]/domain/` | — | `test_domains.py` + e2e |
| F23: Webhooks | `api/store_webhooks.py`, `services/webhook_service.py` | `stores/[id]/webhooks/` | — | `test_store_webhooks.py` + e2e |
| F24: Teams | `api/teams.py`, `services/team_service.py` | `stores/[id]/team/` | — | `test_teams.py` + e2e |
| F25: Notifications | `api/notifications.py`, `services/notification_service.py` | `notifications/` | — | `test_notifications.py` + e2e |
| F26: Bulk Ops | `api/bulk.py`, `services/bulk_service.py` | `stores/[id]/bulk/` | — | `test_bulk.py` + e2e |
| F27: CDN/Perf | — | — | PWA, optimized images | — |
| F28: Fraud | `api/fraud.py`, `services/fraud_service.py` | `stores/[id]/fraud/` | — | `test_fraud.py` + e2e |
| F29: A/B Testing | `api/ab_tests.py`, `services/ab_test_service.py` | `stores/[id]/ab-tests/` | — | `test_ab_tests.py` + e2e |
| F30: PWA | — | — | `manifest.json`, `sw.js` | — |

### Frontend Bug Fixes Discovered During E2E Testing

During populated-data e2e testing, several classes of frontend bugs were uncovered and fixed:

1. **Paginated response unwrapping**: Backend list endpoints return `{ items: [...], total, page, ... }` but frontend pages expected plain arrays, causing `.map is not a function` crashes. Fixed in refunds, reviews, and analytics pages.

2. **Pydantic Decimal serialization**: SQLAlchemy Decimal columns serialize as strings in JSON (e.g., `"25.00"` not `25`). Calling `.toFixed(2)` on strings throws errors. Fixed by wrapping with `Number()`.

3. **Frontend-backend field name mismatches**: TypeScript interfaces had fields that don't exist in backend schemas (e.g., `order_number`, `customer_name`). Fixed by aligning with actual backend response.

4. **String concatenation in reduce()**: `refunds.reduce((sum, r) => sum + r.amount, 0)` produces `"049.99"` when `amount` is a Decimal string. Fixed with `Number()` conversion.

### E2E Testing Approach

Tests live in `e2e/tests/` and use Playwright. Each test file covers:
- **Empty state**: Verifies pages render correctly with no data (empty state messages, create buttons)
- **Populated data**: Seeds real data via API calls and verifies pages render all fields correctly
- **Seed data**: Verifies the demo seed data (Volt Electronics store) is correctly displayed across dashboard and storefront

This triple approach catches bugs that only manifest with real data (Decimal formatting, response unwrapping, field mismatches).

Key test helpers in `e2e/tests/helpers.ts`:
- `apiPost` / `apiGet` with retry logic for race conditions (retries on 400, 401, 404)
- `createOrderAPI`, `createRefundAPI`, `createReviewAPI` for seeding test data
- `createSegmentAPI`, `createCategoryAPI`, etc. for all resource types
- `seedDatabase()` — runs the seed.ts script and returns the store slug for seed data tests

**E2E test files (171 tests across 23 spec files):**

| File | Covers |
|------|--------|
| `dashboard/auth.spec.ts` | User registration, login, redirects |
| `dashboard/stores.spec.ts` | Store CRUD, store listing |
| `dashboard/products.spec.ts` | Product CRUD, populated table |
| `dashboard/orders.spec.ts` | Order listing, detail, status updates |
| `dashboard/fulfillment.spec.ts` | Fulfillment flow, tracking |
| `dashboard/discounts.spec.ts` | Discount CRUD, formatted values |
| `dashboard/categories.spec.ts` | Category CRUD, nested subcategories |
| `dashboard/suppliers.spec.ts` | Supplier CRUD, linked products |
| `dashboard/gift-cards.spec.ts` | Gift card CRUD, formatted balances |
| `dashboard/tax-refunds.spec.ts` | Tax rates + refunds, Decimal formatting |
| `dashboard/teams-webhooks.spec.ts` | Team invites + webhook config |
| `dashboard/reviews-analytics.spec.ts` | Reviews + analytics pages |
| `dashboard/currency-domain.spec.ts` | Currency settings + domain config |
| `dashboard/advanced-features.spec.ts` | Segments, upsells, A/B tests, bulk ops |
| `dashboard/themes-email.spec.ts` | Theme settings + email templates |
| `dashboard/billing.spec.ts` | Billing page, subscription |
| `dashboard/seed-data.spec.ts` | Seed data verification (24 tests) |
| `storefront/browse.spec.ts` | Product browsing, homepage |
| `storefront/cart-checkout.spec.ts` | Cart, checkout, payment |
| `storefront/categories-search.spec.ts` | Category nav + search |
| `storefront/customer-accounts.spec.ts` | Customer auth, orders, wishlist |
| `storefront/policies.spec.ts` | Policy pages |
| `storefront/seed-data.spec.ts` | Seed data verification (12 tests) |

---

### Feature 8: Discount Codes & Promotions ✅
**Priority:** Critical | **Estimated effort:** Medium | **Impact:** Direct revenue driver — every ecommerce store needs this
**Status:** Complete

### What we're building
Discount codes, automatic discounts, and promotional pricing. Inspired by Shopify's discount engine (percentage, fixed amount, BOGO, free shipping) and BigCommerce's 70+ promotion types.

### Why this matters for dropshipping
- **Conversion:** Discount codes are the #1 tool to convert hesitant first-time buyers on new stores
- **Marketing campaigns:** Every email/social campaign needs a promo code — essential for Feature A4 (Email Marketing)
- **Average order value:** Tiered discounts ("spend $50 get 10% off") increase cart size, improving margins
- **Competitive edge:** New dropshipping stores compete on perceived value — discounts create urgency

### Acceptance criteria
- [ ] `POST /api/v1/stores/{store_id}/discounts` — create discount
- [ ] `GET /api/v1/stores/{store_id}/discounts` — list discounts with pagination
- [ ] `PATCH /api/v1/stores/{store_id}/discounts/{id}` — update discount
- [ ] `DELETE /api/v1/stores/{store_id}/discounts/{id}` — deactivate discount
- [ ] Discount types: percentage off, fixed amount off, free shipping, buy X get Y
- [ ] Discount scope: entire order, specific products, specific collections
- [ ] Automatic discounts (apply at cart without code) and code-based discounts
- [ ] Usage limits: total uses, per-customer limit, minimum order amount
- [ ] Expiration dates (start/end)
- [ ] Stackable vs. non-stackable discounts
- [ ] `POST /api/v1/public/stores/{slug}/cart/apply-discount` — validate and apply discount code
- [ ] Discount reflected in Stripe Checkout session
- [ ] Dashboard: discount creation form, discount list, usage analytics
- [ ] Storefront: discount code input at cart/checkout, automatic discount display
- [ ] Alembic migration for `discounts` table

### Tasks
- [P] Create `Discount` model (id, store_id, code, type, value, scope, min_order, usage_limit, used_count, starts_at, ends_at, is_automatic, status)
- [P] Create `DiscountRule` model for complex conditions (buy X get Y, product-specific)
- [P] Alembic migration
- [P] Pydantic schemas (CreateDiscount, UpdateDiscount, DiscountResponse, ApplyDiscountRequest)
- [P] Discount service (create, validate, apply, calculate, track usage)
- [P] Discount router (CRUD, scoped to store)
- [P] Public discount endpoint (validate + apply at checkout)
- [P] Integrate discount into Stripe Checkout session (line item adjustments or coupons)
- [P] Tests for all discount endpoints and edge cases
- [N] Dashboard: discount creation form (type selector, conditions builder, date picker)
- [N] Dashboard: discount list page with usage stats
- [N] Storefront: discount code input field in cart
- [N] Storefront: automatic discount banner/badge display
- [N] Storefront: discount summary in order confirmation

---

### Feature 9: Product Categories & Collections ✅
**Priority:** Critical | **Estimated effort:** Medium | **Impact:** Fundamental product organization — affects discoverability and SEO
**Status:** Complete

### What we're building
Hierarchical product categories and curated collections (manual + automated rules). Modeled after Shopify's collections and WooCommerce's category/tag system.

### Why this matters for dropshipping
- **Product discovery:** Dropshipping stores often have 100-500+ products — without categories, stores are unusable
- **SEO:** Category pages are major organic traffic drivers (e.g., "/collections/trending-gadgets")
- **Auto-collections:** Rules like "added in last 7 days" or "price under $20" work perfectly with auto-imported products
- **Discount targeting:** Feature 8 (discounts) can target specific collections ("20% off all kitchen gadgets")
- **Niche organization:** Dropshipping stores are niche-based — categories reflect the niche taxonomy

### Acceptance criteria
- [ ] `POST /api/v1/stores/{store_id}/categories` — create category (supports parent_id for hierarchy)
- [ ] `GET /api/v1/stores/{store_id}/categories` — list categories as tree
- [ ] `PATCH /api/v1/stores/{store_id}/categories/{id}` — update category
- [ ] `DELETE /api/v1/stores/{store_id}/categories/{id}` — delete category (reassign products)
- [ ] `POST /api/v1/stores/{store_id}/collections` — create collection (manual or automated)
- [ ] Automated collections: rules-based (e.g., "price > $50", "tag = summer", "created in last 30 days")
- [ ] Products can belong to multiple categories and collections
- [ ] Category/collection pages on storefront with filtering and sorting
- [ ] SEO metadata per category/collection (title, description, slug)
- [ ] Dashboard: category tree manager, collection builder with rule editor
- [ ] Storefront: navigation by categories, collection pages with product grid
- [ ] Public API: `GET /api/v1/public/stores/{slug}/categories`, `/collections/{slug}`
- [ ] Alembic migration for `categories`, `collections`, `product_categories`, `product_collections` tables

### Tasks
- [P] Create `Category` model (id, store_id, parent_id, name, slug, description, image, position, seo_title, seo_description)
- [P] Create `Collection` model (id, store_id, name, slug, description, image, type[manual/automated], rules, seo_title, seo_description)
- [P] Create junction tables: `product_categories`, `product_collections`
- [P] Alembic migration
- [P] Pydantic schemas
- [P] Category service (CRUD, tree building, product assignment)
- [P] Collection service (CRUD, rule evaluation engine for automated collections)
- [P] Category and collection routers
- [P] Public endpoints for categories and collections
- [P] Tests
- [N] Dashboard: category tree manager (drag-and-drop reordering)
- [N] Dashboard: collection builder with visual rule editor
- [N] Dashboard: assign categories/collections when creating/editing products
- [N] Storefront: category navigation in header/sidebar
- [N] Storefront: collection page with product grid, filtering, sorting
- [N] Storefront: breadcrumb navigation

---

### Feature 10: Supplier Management & Order Fulfillment ✅
**Priority:** Critical | **Estimated effort:** Large | **Impact:** Core dropshipping operation — links orders to suppliers
**Status:** Complete

### What we're building
Supplier management system that links products to their source suppliers (AliExpress, CJ Dropshipping, etc.), tracks supplier cost/pricing, and automates order fulfillment by placing orders with suppliers when a customer buys. This is the operational backbone of the dropshipping model.

### Why this matters for dropshipping
- **Core to the business model:** Dropshipping IS supplier management — without this, every order requires manual supplier ordering
- **Profit tracking:** Store owners need to know cost vs. retail price for every product to understand actual margins
- **Fulfillment automation:** Auto-ordering from suppliers when a customer pays eliminates the biggest manual bottleneck
- **Supplier reliability:** Tracking delivery times and quality helps store owners choose better suppliers
- **Scale:** The master plan promises "scale without increasing manual workload" — this feature delivers that promise

### Acceptance criteria
- [ ] `POST /api/v1/stores/{store_id}/suppliers` — register a supplier source (platform, API credentials)
- [ ] `GET /api/v1/stores/{store_id}/suppliers` — list suppliers
- [ ] Link products to suppliers: supplier_url, supplier_product_id, supplier_cost
- [ ] Product cost (supplier price) stored alongside retail price — profit margin visible per product
- [ ] Auto-fulfill: when order is paid, auto-order from supplier (AliExpress, CJ Dropshipping API)
- [ ] Manual fulfill fallback: mark order for manual fulfillment with supplier link
- [ ] Supplier order tracking: store supplier order ID and tracking number per order
- [ ] Auto-import tracking number from supplier (polling or webhook)
- [ ] Customer receives tracking number via email (integrates with Feature 11)
- [ ] Fulfillment status flow: pending → ordered_from_supplier → supplier_shipped → delivered
- [ ] Dashboard: supplier management page (add/edit/remove suppliers)
- [ ] Dashboard: order fulfillment page (auto-fulfill status, manual fulfill button)
- [ ] Dashboard: product profit margin display (retail - supplier cost - fees)
- [ ] Dashboard: supplier performance metrics (avg delivery time, order success rate)
- [ ] Alembic migration for `suppliers`, `supplier_products`, `fulfillments` tables

### Tasks
- [P] Create `Supplier` model (id, store_id, name, platform[aliexpress/cj/custom], api_credentials, status)
- [P] Create `SupplierProduct` model (id, product_id, supplier_id, supplier_product_id, supplier_url, supplier_cost, supplier_shipping_cost, last_checked)
- [P] Create `Fulfillment` model (id, order_id, supplier_id, supplier_order_id, tracking_number, tracking_url, carrier, status, cost, ordered_at, shipped_at, delivered_at)
- [P] Alembic migration
- [P] Supplier service (CRUD, credential validation)
- [P] Fulfillment service (auto-order from supplier, track status, import tracking)
- [P] AliExpress fulfillment integration (place order via API or affiliate link)
- [P] CJ Dropshipping API integration (order placement, tracking)
- [P] Celery task: auto_fulfill_order (triggered on order.paid event)
- [P] Celery task: poll_supplier_tracking (periodic, check for tracking updates)
- [P] Supplier router (CRUD)
- [P] Fulfillment router (fulfill, status, tracking)
- [P] Profit calculation utility (retail - cost - shipping - fees)
- [P] Tests
- [N] Dashboard: supplier management page (add API credentials, test connection)
- [N] Dashboard: product supplier linking (when creating/editing products)
- [N] Dashboard: order fulfillment page (status badges, auto-fulfill toggle, manual fulfill button)
- [N] Dashboard: profit margin display on product list and detail
- [N] Dashboard: supplier performance dashboard (avg delivery time, success rate)

---

### Feature 11: Transactional Email Notifications ✅
**Priority:** Critical | **Estimated effort:** Medium | **Impact:** Expected by every customer — absence erodes trust
**Status:** Complete

### What we're building
Automated transactional emails for key order lifecycle events. Using SendGrid or AWS SES. These are essential operational emails (distinct from marketing automation in Feature A4).

### Why this matters for dropshipping
- **Customer trust:** Dropshipping has longer shipping times (7-21 days from suppliers) — constant communication is critical
- **"Where is my order?":** The #1 support request. Automated tracking emails reduce support load by 80%+
- **Chargeback prevention:** No confirmation email = customer anxiety = chargebacks ($15+ each)
- **Legal:** Many jurisdictions require purchase receipts
- **Supplier shipping awareness:** Customers need to know shipping comes from overseas and may take longer

### Acceptance criteria
- [ ] Order confirmation email (sent on successful payment)
- [ ] Order fulfilled / shipped email with tracking number and link
- [ ] Delivery confirmation email
- [ ] Order cancellation/refund email
- [ ] Customer welcome email on account creation
- [ ] Password reset email (implement actual reset flow, currently stubbed)
- [ ] Store owner: new order notification email
- [ ] Shipping time expectation email ("your order is being prepared by our supplier")
- [ ] HTML email templates (responsive, branded per store)
- [ ] Template customization via dashboard (store logo, colors, footer text)
- [ ] Email delivery tracking (sent, delivered, opened, clicked)
- [ ] Celery tasks for async email sending (retry on failure)
- [ ] Dashboard: email template preview and customization
- [ ] Dashboard: email delivery log

### Tasks
- [P] Email service abstraction (SendGrid SDK / AWS SES, switchable)
- [P] Create `EmailTemplate` model (id, store_id, type, subject, html_body, is_custom)
- [P] Create `EmailLog` model (id, store_id, recipient, template_type, status, sent_at, opened_at, clicked_at)
- [P] Alembic migration
- [P] Default HTML email templates (Jinja2, responsive, dropshipping-aware copy)
- [P] Celery tasks: send_order_confirmation, send_shipping_update, send_welcome_email, etc.
- [P] Integrate with order status change hooks (order paid → send confirmation, fulfilled → send tracking)
- [P] Implement actual password reset flow (generate token, send email, reset endpoint)
- [P] Tests
- [N] Dashboard: email template editor (WYSIWYG or code editor)
- [N] Dashboard: email delivery log page
- [N] Dashboard: email settings (sender name, reply-to, logo)
- [N] Storefront: password reset pages (request, confirm)

---

### Feature 12: Product Reviews & Ratings ✅
**Priority:** Critical | **Estimated effort:** Medium | **Impact:** Social proof is the #1 conversion factor after price
**Status:** Complete

### What we're building
Customer product reviews with star ratings, moderation, and aggregate display. Inspired by Amazon's review system and Shopify's review apps.

### Why this matters for dropshipping
- **Trust signal:** New dropshipping stores lack brand recognition — reviews are the primary trust signal
- **Conversion:** Products with reviews convert 270% better than those without (Spiegel Research Center)
- **SEO:** Review schema markup (star ratings in Google search results) dramatically increases click-through
- **Product quality signal:** Reviews help store owners identify which supplier products are actually good vs. problematic
- **User-generated content:** Reviews add unique content that improves SEO

### Acceptance criteria
- [ ] `POST /api/v1/public/stores/{slug}/products/{slug}/reviews` — submit review (requires customer auth)
- [ ] `GET /api/v1/public/stores/{slug}/products/{slug}/reviews` — list reviews with pagination, sorting
- [ ] Star rating (1-5), title, body text, optional images
- [ ] One review per customer per product (can update)
- [ ] Verified purchase badge (customer has ordered this product)
- [ ] Store owner moderation: approve, reject, respond to reviews
- [ ] Aggregate rating calculation (average stars, rating distribution)
- [ ] Review schema markup (JSON-LD) on product pages for SEO
- [ ] Dashboard: review moderation queue, respond to reviews
- [ ] Storefront: review display on product pages, review submission form
- [ ] Storefront: star rating display on product cards in grid
- [ ] Email: request review email after order delivery (Celery task)
- [ ] Alembic migration for `reviews` table

### Tasks
- [P] Create `Review` model (id, store_id, product_id, customer_id, order_id, rating, title, body, images, status[pending/approved/rejected], owner_response, is_verified_purchase)
- [P] Alembic migration
- [P] Pydantic schemas
- [P] Review service (submit, list, moderate, aggregate, verify purchase)
- [P] Public review endpoints (submit, list)
- [P] Store owner review endpoints (list pending, approve, reject, respond)
- [P] Aggregate rating calculation (cached in Redis)
- [P] Review request Celery task (triggered N days after delivery)
- [P] Tests
- [N] Storefront: review display component (stars, text, images, verified badge)
- [N] Storefront: review submission form (star selector, text, image upload)
- [N] Storefront: aggregate rating display on product cards
- [N] Dashboard: review moderation page (approve/reject queue)
- [N] Dashboard: review response form
- [N] Storefront: JSON-LD review schema markup on product pages

---

### Feature 13: Profit & Performance Analytics ✅
**Priority:** Critical | **Estimated effort:** Large | **Impact:** Data-driven decisions — merchants need to understand margins
**Status:** Complete

### What we're building
Dropshipping-focused analytics: profit margins per product/order, revenue vs. COGS, supplier costs, product performance, conversion tracking, and storefront analytics. This is more than a generic dashboard — it's built around dropshipping P&L.

### Why this matters for dropshipping
- **Profit visibility:** The #1 mistake dropshippers make is not knowing their actual margins after supplier costs + fees
- **Product decisions:** Which products are profitable? Which should be removed? Data-driven vs. guessing
- **Supplier comparison:** Compare profit margins across suppliers for the same product
- **Revenue optimization:** Understand which traffic sources and products drive actual profit (not just revenue)
- **Scaling decisions:** Know when to scale ad spend based on per-product ROAS

### Acceptance criteria
- [ ] Dashboard: profit overview (revenue, COGS, gross profit, net margin)
- [ ] Dashboard: profit per product (retail price − supplier cost − shipping − Stripe fees)
- [ ] Dashboard: profit per order (total − all costs)
- [ ] Dashboard: revenue chart (line chart, daily/weekly/monthly)
- [ ] Dashboard: top products by profit (not just by revenue)
- [ ] Dashboard: conversion funnel (visitors → add to cart → checkout → purchase)
- [ ] Dashboard: customer metrics (new vs returning, repeat purchase rate)
- [ ] Date range picker (today, 7d, 30d, 90d, custom range)
- [ ] Comparison with previous period (e.g., this week vs last week)
- [ ] Event tracking: page views, product views, add-to-cart, checkout initiated, purchase
- [ ] Export analytics data as CSV
- [ ] Data aggregated server-side, cached in Redis
- [ ] Alembic migration for `analytics_events` table

### Tasks
- [P] Create `AnalyticsEvent` model (id, store_id, event_type, product_id, customer_id, session_id, metadata, created_at)
- [P] Alembic migration
- [P] Event ingestion endpoint (batch events from storefront)
- [P] Profit calculation service (per product, per order — using supplier cost data from Feature 10)
- [P] Analytics aggregation service (revenue, COGS, profit, conversion funnel, product performance)
- [P] Redis caching for pre-computed aggregations
- [P] Celery task: daily analytics aggregation and caching
- [P] Analytics API endpoints (overview, profit, revenue, products, customers, export)
- [P] Tests
- [N] Storefront: event tracking script (page views, product views, add-to-cart, purchase)
- [N] Dashboard: profit overview page with summary cards (revenue, COGS, profit, margin %)
- [N] Dashboard: revenue + profit chart (Recharts, dual-axis line chart)
- [N] Dashboard: product performance table (sortable by profit, revenue, orders, conversion)
- [N] Dashboard: conversion funnel visualization
- [N] Dashboard: date range picker with comparison toggle
- [N] Dashboard: CSV export button

---

### Feature 14: Refunds & Customer Disputes ✅
**Priority:** High | **Estimated effort:** Medium | **Impact:** Customer trust and chargeback prevention
**Status:** Complete

### What we're building
Refund processing and customer dispute management, adapted for the dropshipping model. Store owners don't handle physical returns — refunds are monetary (via Stripe Refund API) or store credit. Focused on preventing chargebacks and maintaining customer trust.

### Why this matters for dropshipping
- **No physical returns:** Dropshipping customers don't ship products back to the store owner — refunds are monetary
- **Chargeback prevention:** Proper refund flows reduce Stripe chargebacks ($15+ each + product cost)
- **Supplier issues:** Products from suppliers may arrive damaged, wrong, or late — store owner absorbs the loss or disputes with supplier
- **Customer trust:** A clear refund policy is the #2 factor in purchase decisions for unknown stores
- **Long shipping times:** 7-21 day shipping from China means more customer anxiety and dispute potential

### Acceptance criteria
- [ ] Customer can request a refund from their order history
- [ ] `POST /api/v1/public/stores/{slug}/account/orders/{id}/refund-request` — create refund request
- [ ] Refund reasons: not received, damaged, not as described, changed mind, other
- [ ] Refund statuses: requested → approved → refunded (or rejected)
- [ ] Store owner approves/rejects refund requests from dashboard
- [ ] Full and partial refunds via Stripe Refund API
- [ ] Store credit option (as alternative to monetary refund)
- [ ] Refund amount calculation (item price, configurable restocking fee)
- [ ] Email notifications at each refund status change (uses Feature 11)
- [ ] Dashboard: refund management page (pending, approved, completed)
- [ ] Dashboard: refund processing interface (approve, reject, partial refund)
- [ ] Dashboard: refund policy editor (refund window, conditions)
- [ ] Dashboard: supplier dispute tracking (note which refunds are due to supplier issues)
- [ ] Storefront: refund request form in customer account
- [ ] Storefront: refund status tracking
- [ ] Alembic migration for `refund_requests`, `refunds`, `store_credits` tables

### Tasks
- [P] Create `RefundRequest` model (id, store_id, order_id, customer_id, status, reason, notes, supplier_issue)
- [P] Create `Refund` model (id, store_id, order_id, refund_request_id, stripe_refund_id, amount, type[monetary/store_credit], status)
- [P] Create `StoreCredit` model (id, store_id, customer_id, balance, created_from_refund_id)
- [P] Alembic migration
- [P] Pydantic schemas
- [P] Refund service (request, approve, reject, process via Stripe)
- [P] Store credit service (balance management, apply at checkout)
- [P] Refund router (customer-facing + store owner endpoints)
- [P] Email notifications for refund status changes
- [P] Tests
- [N] Dashboard: refund requests list with status filters
- [N] Dashboard: refund detail page (approve/reject, process refund, note supplier issue)
- [N] Dashboard: refund policy settings
- [N] Storefront: refund request form
- [N] Storefront: refund status tracking in customer account
- [N] Storefront: store credit balance display and checkout integration

---

### Feature 15: Store Customization & Themes ✅
**Priority:** High | **Estimated effort:** Large | **Impact:** Brand identity — stores must look unique, not template-generic
**Status:** Complete

### What we're building
Store theming system with customizable colors, fonts, logos, custom pages, and navigation menus. Store owners need their dropshipping store to look like a real brand, not a generic template.

### Why this matters for dropshipping
- **Trust:** Professional-looking stores convert 2x better than template-looking ones
- **Brand perception:** Customers distrust stores that look like every other dropshipping store
- **Content pages:** About Us, Contact, FAQ, Shipping Policy (explaining supplier shipping times) — every store needs these
- **Differentiation:** Store owners choose platforms partly based on customization ability
- **Shipping policy:** Dropshipping stores MUST have a clear shipping policy explaining longer delivery times

### Acceptance criteria
- [ ] Store branding settings: logo, favicon, primary color, secondary color, accent color
- [ ] Font selection (from curated list of Google Fonts)
- [ ] Homepage layout customization (hero banner, featured collections, testimonials)
- [ ] Custom pages builder (About Us, Contact, FAQ, Shipping Policy, Returns Policy)
- [ ] WYSIWYG content editor for custom pages (rich text, images, embeds)
- [ ] Navigation menu editor (header, footer, custom links)
- [ ] Announcement bar (configurable text, color, link — great for "Free shipping over $X")
- [ ] Social media links (Instagram, Facebook, TikTok, X, YouTube)
- [ ] Store footer customization (columns, links, newsletter signup)
- [ ] Theme presets (3-5 pre-built color/font combinations)
- [ ] Dashboard: store appearance settings page
- [ ] Dashboard: custom page editor
- [ ] Dashboard: navigation menu editor
- [ ] Storefront: dynamic styling from store settings
- [ ] API: `GET /api/v1/public/stores/{slug}/theme`

### Tasks
- [P] Create `StoreTheme` model (id, store_id, logo_url, favicon_url, primary_color, secondary_color, accent_color, font_heading, font_body, hero_config, announcement_bar, social_links)
- [P] Create `CustomPage` model (id, store_id, title, slug, content, seo_title, seo_description, is_published, position)
- [P] Create `NavigationMenu` model (id, store_id, location[header/footer], items[JSON])
- [P] Alembic migration
- [P] Theme service (CRUD, preset application)
- [P] Custom page service (CRUD)
- [P] Navigation service (CRUD)
- [P] Public endpoints (theme settings, custom pages, navigation)
- [P] Tests
- [N] Dashboard: appearance settings (color pickers, font selectors, logo upload)
- [N] Dashboard: theme preset selector with preview
- [N] Dashboard: custom page editor with WYSIWYG (TipTap or Plate)
- [N] Dashboard: navigation menu editor (drag-and-drop, nested items)
- [N] Dashboard: announcement bar editor
- [N] Storefront: CSS variable system driven by theme settings
- [N] Storefront: custom page rendering at `/{page-slug}`
- [N] Storefront: dynamic navigation from menu settings
- [N] Storefront: announcement bar component

---

### Feature 16: Tax Calculation ✅
**Priority:** High | **Estimated effort:** Medium | **Impact:** Legal compliance — required for legitimate ecommerce
**Status:** Complete

### What we're building
Automatic tax calculation based on customer location. Optionally integrates with tax services (TaxJar, Avalara) or uses built-in rate tables.

### Why this matters for dropshipping
- **Legal requirement:** Sales tax collection is mandatory in most US states; VAT in EU/UK
- **Customer expectation:** Tax at checkout prevents surprise costs (cart abandonment)
- **Simplified for dropshipping:** Most dropshippers are US-based selling domestically — start with US sales tax
- **Growth path:** As stores grow internationally, need EU VAT support

### Acceptance criteria
- [ ] Tax calculated automatically based on shipping address
- [ ] US sales tax: state rates (simplified — one rate per state)
- [ ] Basic international VAT support (EU, UK, Canada, Australia)
- [ ] Tax-exempt products (digital goods)
- [ ] Manual tax rate override per store (for simple setups)
- [ ] Tax rate lookup via external service (TaxJar API) or built-in rate tables
- [ ] Tax displayed as separate line item at checkout
- [ ] Tax included in Stripe Checkout session
- [ ] Dashboard: tax settings page (regions, rates)
- [ ] Dashboard: tax report (total collected, by jurisdiction)
- [ ] Orders store tax amount for reporting
- [ ] Alembic migration for `tax_rates` table

### Tasks
- [P] Create `TaxRate` model (id, store_id, country, state, rate, name)
- [P] Alembic migration
- [P] Tax calculation service (address → applicable rate → tax amount)
- [P] Built-in US state tax rate table (base rates)
- [P] TaxJar API integration (optional, for real-time rates)
- [P] Tax router (settings CRUD, rate lookup)
- [P] Integrate tax into checkout flow (add tax line to Stripe session)
- [P] Update Order model to store tax_amount
- [P] Tax reporting service (aggregate by jurisdiction and period)
- [P] Tests
- [N] Dashboard: tax settings page (enable/disable, rate table)
- [N] Dashboard: tax report page
- [N] Storefront: tax line item in cart and checkout

---

### Feature 17: Advanced Search & Filtering ✅
**Priority:** High | **Estimated effort:** Medium | **Impact:** Product discovery — directly affects conversion
**Status:** Complete

### What we're building
Full-text search with autocomplete, faceted filtering, and smart sorting. Dropshipping stores with 100+ products need proper search.

### Why this matters for dropshipping
- **Large catalogs:** Dropshipping stores often have 100-500+ products (auto-imported) — search is essential
- **Conversion:** Site search users convert 2-3x higher than browsers (Forrester Research)
- **Faceted filtering:** Customers expect to filter by price range, category, rating

### Acceptance criteria
- [ ] Full-text search across product title, description, tags, SKU
- [ ] Search autocomplete/suggestions (as-you-type)
- [ ] Faceted filtering: price range, category, collection, rating, in-stock
- [ ] Sort options: relevance, price (low/high), newest, best selling, top rated
- [ ] Search results page with result count and active filters
- [ ] Search analytics (what customers search for, zero-result queries)
- [ ] PostgreSQL full-text search with tsvector (GIN index)
- [ ] Public API: `GET /api/v1/public/stores/{slug}/search?q=...&filters=...`
- [ ] Dashboard: search analytics page (top queries, zero-result queries)
- [ ] Storefront: search bar with autocomplete dropdown
- [ ] Storefront: search results page with faceted filters sidebar

### Tasks
- [P] Add tsvector column to products table (GIN index)
- [P] Alembic migration for search index
- [P] Search service (full-text query, facet aggregation, autocomplete)
- [P] Search analytics tracking (log queries, results count)
- [P] Create `SearchQuery` model (store_id, query, results_count, customer_id, created_at)
- [P] Public search endpoint with faceted filters
- [P] Search analytics endpoint (store owner)
- [P] Tests
- [N] Storefront: search bar component with autocomplete dropdown
- [N] Storefront: search results page with faceted filter sidebar
- [N] Storefront: active filter chips with remove functionality
- [N] Dashboard: search analytics page (top queries, trending, zero-result)

---

### Feature 18: Upsell, Cross-sell & Product Recommendations ✅
**Priority:** High | **Estimated effort:** Medium | **Impact:** Increases average order value by 10-30%
**Status:** Complete

### What we're building
Product recommendation engine with "Frequently bought together", "You may also like", and cart upsells. Inspired by Amazon's recommendation engine (35% of their revenue).

### Why this matters for dropshipping
- **Average order value:** Upsells at cart increase AOV by 10-30% — critical for thin dropshipping margins
- **Discovery:** Helps customers find products in your large auto-imported catalog
- **Cross-sell complementary items:** Kitchen gadgets pair naturally (e.g., spatula + cutting board)
- **Post-purchase offers:** Upsell on confirmation page while customer is in buying mode

### Acceptance criteria
- [ ] "Related Products" section on product detail page (same category/collection)
- [ ] "Frequently Bought Together" on product page (based on co-purchase data)
- [ ] "You May Also Like" recommendations (based on browsing/purchase history)
- [ ] Cart upsell: suggest complementary products in cart
- [ ] Post-purchase upsell: offer on order confirmation page
- [ ] Manual recommendations: store owner can set related products per product
- [ ] Algorithm-based recommendations: co-purchase analysis
- [ ] Dashboard: recommendation settings, manual product linking
- [ ] Storefront: recommendation carousels on product, cart, and homepage

### Tasks
- [P] Create `ProductRelation` model (id, store_id, product_id, related_product_id, type[manual/co_purchase/similar], score)
- [P] Alembic migration
- [P] Recommendation service (co-purchase analysis, content similarity, manual relations)
- [P] Celery task: compute_recommendations (nightly, analyze order data)
- [P] Recommendation API endpoints (by product, personalized, cart-based)
- [P] Tests
- [N] Storefront: "Related Products" carousel
- [N] Storefront: "Frequently Bought Together" bundle
- [N] Storefront: cart upsell sidebar/drawer
- [N] Storefront: post-purchase offer on confirmation page
- [N] Dashboard: recommendation settings and manual linking

---

### Feature 19: Customer Segmentation & Groups ✅
**Priority:** Medium | **Estimated effort:** Medium | **Impact:** Targeted marketing improves conversion 5-10x
**Status:** Complete

### What we're building
Customer segments based on behavior, purchase history, and attributes. Powers targeted email campaigns (Feature A4) and personalized discounts.

### Why this matters for dropshipping
- **Targeted marketing:** "Customers who bought kitchen gadgets" → send them the new kitchen product email
- **Win-back:** Identify lapsed customers before they churn
- **VIP treatment:** High-value repeat customers get exclusive discounts
- **Marketing efficiency:** Stop sending blanket discounts — target only those who need them

### Acceptance criteria
- [ ] Pre-built segments: "New Customers", "Repeat Buyers", "VIP (top 10%)", "At Risk", "Lapsed"
- [ ] Custom segment builder: combine conditions (spent > $X, ordered > N times, last order > N days ago)
- [ ] Customer tags (free-form labels)
- [ ] Segment-based export (CSV) for email marketing tools
- [ ] Segment customer counts auto-refreshed
- [ ] Dashboard: segment list with customer counts
- [ ] Dashboard: segment builder with visual rule editor

### Tasks
- [P] Create `CustomerSegment` model (id, store_id, name, rules[JSON], is_preset, customer_count)
- [P] Alembic migration
- [P] Segment evaluation engine (run rules against customer data, cache results)
- [P] Celery task: refresh_segments (daily re-evaluation)
- [P] Segment router (CRUD)
- [P] Tests
- [N] Dashboard: segments list page with customer counts
- [N] Dashboard: visual segment builder (condition groups, AND/OR logic)
- [N] Dashboard: export segment to CSV

---

### Feature 20: Gift Cards ✅
**Priority:** Medium | **Estimated effort:** Medium | **Impact:** Revenue + customer acquisition + retention
**Status:** Complete

### What we're building
Digital gift cards purchasable on storefront, delivered via email, redeemable at checkout.

### Why this matters for dropshipping
- **Revenue:** Gift cards are upfront revenue — 10-15% are never redeemed (breakage)
- **Customer acquisition:** Gift recipients become new customers
- **Seasonal:** Gift cards are the #1 purchased item during holidays
- **No supplier involvement:** Gift cards are purely digital — no fulfillment needed

### Acceptance criteria
- [ ] Gift cards purchasable as a product on storefront
- [ ] Denominations: fixed amounts ($25, $50, $100) or custom amount
- [ ] Gift card delivery via email to recipient
- [ ] Unique gift card code (16-char alphanumeric)
- [ ] Redeem at checkout (partial or full balance)
- [ ] Gift card balance tracking
- [ ] Dashboard: gift card management (issue, view balance, disable)
- [ ] Storefront: gift card product page, redemption at checkout, balance check
- [ ] Alembic migration for `gift_cards`, `gift_card_transactions` tables

### Tasks
- [P] Create `GiftCard` model (id, store_id, code, initial_balance, current_balance, recipient_email, message, status, expires_at)
- [P] Create `GiftCardTransaction` model (id, gift_card_id, order_id, amount, type[purchase/redemption], created_at)
- [P] Alembic migration
- [P] Gift card service (create, purchase, redeem, check balance)
- [P] Gift card code generation utility
- [P] Integrate gift card redemption into checkout flow
- [P] Gift card delivery email
- [P] Tests
- [N] Dashboard: gift card management page
- [N] Storefront: gift card product page
- [N] Storefront: gift card code input at checkout
- [N] Storefront: gift card balance check page

---

### Feature 21: Multi-Currency & International ✅
**Priority:** Medium | **Estimated effort:** Medium | **Impact:** Expands addressable market globally
**Status:** Complete

### What we're building
Multi-currency support with automatic exchange rate conversion. Dropshipping is inherently global.

### Why this matters for dropshipping
- **Global customers:** Dropshipping ships worldwide from suppliers — customers are international
- **Conversion:** Showing local currency increases conversion by 12-15% (CSA Research)
- **Stripe support:** Stripe natively supports multi-currency checkout

### Acceptance criteria
- [ ] Store can enable multiple currencies (USD, EUR, GBP, CAD, AUD, etc.)
- [ ] Automatic exchange rate updates (Open Exchange Rates API)
- [ ] Currency selector on storefront (auto-detect from IP or manual)
- [ ] Prices displayed in selected currency
- [ ] Checkout in selected currency (Stripe multi-currency)
- [ ] Dashboard: currency settings (enabled currencies, rates)
- [ ] Orders store original currency and base currency amount

### Tasks
- [P] Create `StoreCurrency` model (id, store_id, currency_code, exchange_rate, is_base, is_enabled)
- [P] Alembic migration
- [P] Currency conversion service (rate fetching, conversion)
- [P] Celery task: update_exchange_rates (daily)
- [P] Update order model for currency tracking
- [P] Public endpoint: prices in requested currency
- [P] Tests
- [N] Dashboard: currency settings page
- [N] Storefront: currency selector component

---

### Feature 22: Custom Domains ✅
**Priority:** Medium | **Estimated effort:** Medium | **Impact:** Professional appearance — builds brand trust
**Status:** Complete

### What we're building
Store owners connect their own custom domain (e.g., mystore.com) with automatic SSL via Let's Encrypt.

### Why this matters for dropshipping
- **Trust:** `mystore.com` looks more legitimate than `mystore.platform.com` — critical for new stores
- **SEO:** Custom domains build domain authority
- **Brand ownership:** Merchants own their brand equity
- **Master plan alignment:** Custom domains are a premium feature in the pricing tiers

### Acceptance criteria
- [ ] Store owner adds custom domain from dashboard
- [ ] DNS verification (CNAME or A record)
- [ ] Automatic SSL certificate provisioning (Let's Encrypt)
- [ ] Domain health check (DNS propagation, SSL status)
- [ ] Multiple domains per store (primary + redirects)
- [ ] Dashboard: domain management page (add, verify, remove)
- [ ] Dashboard: DNS instructions for the store owner
- [ ] Platform routing: custom domain → correct store

### Tasks
- [P] Create `StoreDomain` model (id, store_id, domain, is_primary, dns_verified, ssl_status)
- [P] Alembic migration
- [P] Domain verification service (DNS lookup)
- [P] SSL provisioning integration (cert-manager or ACME)
- [P] Domain router (add, verify, remove)
- [P] Celery task: verify_domain_dns (periodic check)
- [P] Tests
- [K] Ingress controller for dynamic domain routing
- [K] cert-manager ClusterIssuer for Let's Encrypt
- [N] Dashboard: domain management page
- [N] Dashboard: DNS setup instructions
- [N] Storefront: middleware to resolve store from custom domain

---

### Feature 23: Webhooks & Public API ✅
**Priority:** Medium | **Estimated effort:** Medium | **Impact:** Extensibility and third-party integrations
**Status:** Complete

### What we're building
Public REST API with API keys for programmatic store management, and outgoing webhooks for real-time event notifications.

### Why this matters for dropshipping
- **Third-party tools:** Merchants use accounting tools, analytics, CRMs that need API access
- **Custom automation:** Power users build custom workflows via API
- **Platform ecosystem:** Webhooks enable third-party apps to react to store events
- **Master plan alignment:** Pro tier includes API access

### Acceptance criteria
- [ ] API key management (create, revoke, rotate)
- [ ] API key scopes/permissions (read products, write orders, etc.)
- [ ] Rate limiting per API key
- [ ] Outgoing webhooks: configurable per event type
- [ ] Webhook events: order.created, order.updated, product.created, product.updated, customer.created
- [ ] Webhook delivery with retry logic and HMAC signing
- [ ] Webhook delivery log
- [ ] Dashboard: API key management page
- [ ] Dashboard: webhook configuration and delivery log

### Tasks
- [P] Create `ApiKey` model (id, store_id, name, key_hash, scopes, last_used_at, is_active)
- [P] Create `WebhookEndpoint` model (id, store_id, url, events, secret, is_active)
- [P] Create `WebhookDelivery` model (id, endpoint_id, event, payload, response_status, attempts)
- [P] Alembic migration
- [P] API key auth middleware (validate key, check scopes, rate limit)
- [P] Webhook delivery service (HTTP POST with HMAC signing, retry)
- [P] Event dispatcher (emit events on order/product/customer changes)
- [P] Celery task: deliver_webhook (exponential backoff retries)
- [P] Tests
- [N] Dashboard: API key management
- [N] Dashboard: webhook endpoint configuration
- [N] Dashboard: webhook delivery log

---

### Feature 24: Multi-User & Team Access ✅
**Priority:** Medium | **Estimated effort:** Medium | **Impact:** Operational scalability for growing stores
**Status:** Complete

### What we're building
Multi-user access for stores with role-based permissions. Store owners can invite team members (VAs, marketing staff) with granular access.

### Why this matters for dropshipping
- **Virtual assistants:** Successful dropshippers hire VAs to handle order management and customer support
- **Marketing team:** Growing stores have dedicated marketing staff who need dashboard access
- **Security:** VAs shouldn't access billing or store settings — need role-based permissions
- **Scaling path:** The platform's promise is "scale without increasing workload" — team access enables delegation

### Acceptance criteria
- [ ] Store owner can invite team members by email
- [ ] Predefined roles: Owner, Admin, Product Manager, Order Manager, Support, Viewer
- [ ] Custom roles with granular permissions
- [ ] Team member accepts invite and creates account
- [ ] Activity log per team member
- [ ] Dashboard: team management page (invite, roles, remove)
- [ ] Dashboard: activity log
- [ ] Permission enforcement on all API endpoints

### Tasks
- [P] Create `StoreTeamMember` model (id, store_id, user_id, role, permissions, invited_by, joined_at)
- [P] Create `TeamInvite` model (id, store_id, email, role, token, status, expires_at)
- [P] Create `ActivityLog` model (id, store_id, user_id, action, resource_type, resource_id, metadata)
- [P] Alembic migration
- [P] Permission service and team management service
- [P] Activity logging middleware
- [P] Team router
- [P] Tests
- [N] Dashboard: team management page
- [N] Dashboard: invite dialog
- [N] Dashboard: activity log page

---

### Feature 25: Notifications & Alerts Center ✅
**Priority:** Medium | **Estimated effort:** Medium | **Impact:** Keeps merchants informed and responsive
**Status:** Complete

### What we're building
In-app notification center with real-time alerts for orders, supplier issues, product research results, and system events.

### Why this matters for dropshipping
- **Order alerts:** Real-time order notifications help with quick fulfillment
- **Supplier alerts:** Know immediately when a supplier product goes out of stock or price changes
- **Research alerts:** Get notified about high-potential product discoveries
- **Operational awareness:** Low stock alerts, failed fulfillments, chargebacks need immediate attention

### Acceptance criteria
- [ ] In-app notification center (bell icon with unread count)
- [ ] Notification types: new order, fulfillment status, research results, supplier alerts, system events
- [ ] Real-time delivery via WebSocket (or SSE)
- [ ] Mark as read, mark all as read
- [ ] Notification preferences (enable/disable per type)
- [ ] Dashboard: notification bell with dropdown
- [ ] Dashboard: notification settings page

### Tasks
- [P] Create `Notification` model (id, user_id, store_id, type, title, message, data, is_read)
- [P] Create `NotificationPreference` model (id, user_id, type, in_app, email)
- [P] Alembic migration
- [P] Notification service (create, list, mark read)
- [P] WebSocket endpoint for real-time notifications
- [P] Event hooks: emit notification on order/research/supplier events
- [P] Tests
- [N] Dashboard: notification bell component with dropdown
- [N] Dashboard: notification preferences page

---

### Feature 26: Bulk Operations & Import/Export ✅
**Priority:** Medium | **Estimated effort:** Medium | **Impact:** Operational efficiency for large catalogs
**Status:** Complete

### What we're building
Bulk import/export for products and customers via CSV. Bulk edit operations for managing large auto-imported catalogs.

### Why this matters for dropshipping
- **Large catalogs:** Auto-imported stores can have 500+ products — bulk editing is essential
- **Price updates:** Change markup across 100 products at once
- **Migration:** Import products from existing stores on other platforms
- **Data export:** Export orders/products for accounting

### Acceptance criteria
- [ ] Product CSV import (create + update, with variant support)
- [ ] Product CSV export (all fields, with filtering)
- [ ] Order CSV export (with date range filter)
- [ ] Bulk product edit: update price, status, category for selected products
- [ ] Background processing for large imports (Celery task with progress)
- [ ] Import validation with error report
- [ ] Dashboard: import/export page with file upload
- [ ] Dashboard: bulk edit interface

### Tasks
- [P] CSV import/export services
- [P] Create `ImportJob` model (id, store_id, type, status, total_rows, processed_rows, errors)
- [P] Alembic migration
- [P] Celery task: process_import (chunked processing)
- [P] Bulk update service
- [P] Import/export router
- [P] Tests
- [N] Dashboard: import page (file upload, mapping, validation)
- [N] Dashboard: export page (type selector, filters)
- [N] Dashboard: bulk edit interface

---

### Feature 27: Store Performance & CDN ✅
**Priority:** Medium | **Estimated effort:** Medium | **Impact:** SEO and conversion optimization
**Status:** Complete

### What we're building
Image optimization pipeline, CDN integration, and Core Web Vitals monitoring.

### Why this matters for dropshipping
- **Image heavy:** Auto-imported product images from suppliers are often unoptimized and large
- **SEO:** Google ranks faster sites higher (Core Web Vitals)
- **Conversion:** Every 100ms of latency reduces conversion by 1%
- **Image optimization:** Product images are 70-90% of page weight

### Acceptance criteria
- [ ] Image optimization: auto-convert to WebP, generate multiple sizes, lazy load
- [ ] CDN integration (Cloudflare R2 or S3 + CloudFront)
- [ ] Server-side caching (Redis) for product pages and API responses
- [ ] Core Web Vitals monitoring
- [ ] Dashboard: performance score display
- [ ] Storefront: optimized image loading

### Tasks
- [P] Image optimization service (Pillow: resize, WebP, quality)
- [P] CDN upload service (S3/R2)
- [P] API response caching middleware (Redis)
- [P] Celery task: optimize_existing_images
- [P] Tests
- [N] Storefront: next/image optimization with blur placeholders
- [N] Storefront: ISR for product pages
- [N] Dashboard: performance score widget

---

### Feature 28: Fraud Detection ✅
**Priority:** Medium | **Estimated effort:** Medium | **Impact:** Reduces chargebacks and financial loss
**Status:** Complete

### What we're building
Basic fraud detection scoring for orders using Stripe Radar integration and custom velocity checks.

### Why this matters for dropshipping
- **High fraud target:** Dropshipping stores (new brands, unfamiliar names) are frequent fraud targets
- **Chargebacks are costly:** $15+ per incident plus the order amount AND supplier cost (already shipped)
- **Double loss:** Dropshipper loses both the refund AND the supplier payment
- **Stripe Radar:** Built-in fraud scoring we can surface to store owners

### Acceptance criteria
- [ ] Fraud risk score per order (low, medium, high)
- [ ] Stripe Radar score integration
- [ ] Velocity checks (many orders from same IP/email)
- [ ] High-risk orders flagged for manual review before fulfillment
- [ ] Dashboard: fraud risk indicator on order list
- [ ] Dashboard: fraud settings (thresholds, auto-hold rules)

### Tasks
- [P] Fraud scoring service (Stripe Radar, velocity checks)
- [P] Create `FraudCheck` model (id, order_id, score, indicators, action_taken)
- [P] Alembic migration
- [P] Order hold/review workflow
- [P] Tests
- [N] Dashboard: fraud risk badge on orders
- [N] Dashboard: order review queue for flagged orders

---

### Feature 29: A/B Testing ✅
**Priority:** Low | **Estimated effort:** Medium | **Impact:** Data-driven optimization
**Status:** Complete

### What we're building
A/B testing for product titles, prices, descriptions, and images. Essential for optimizing conversion.

### Why this matters for dropshipping
- **Price optimization:** Find the revenue-maximizing price point for each product
- **Title testing:** Test AI-generated vs. manual titles
- **Image testing:** Which product images convert better?
- **Data-driven:** Replace guesswork with statistical evidence

### Acceptance criteria
- [ ] Create A/B test: select element, define variants, set traffic split
- [ ] Testable elements: product title, price, images, description
- [ ] Traffic splitting (cookie-based, consistent per visitor)
- [ ] Statistical significance calculation
- [ ] Test results: conversion rate, revenue per visitor
- [ ] Dashboard: A/B test creation, results, management

### Tasks
- [P] Create `ABTest`, `ABTestAssignment`, `ABTestConversion` models
- [P] Alembic migration
- [P] A/B test service (assign variant, track conversion, calculate significance)
- [P] Tests
- [N] Dashboard: A/B test management
- [N] Storefront: variant rendering middleware

---

### Feature 30: Progressive Web App (PWA) ✅
**Priority:** Low | **Estimated effort:** Small | **Impact:** Mobile engagement
**Status:** Complete

### What we're building
Convert the storefront into a PWA with offline support and install prompt.

### Why this matters for dropshipping
- **Mobile traffic:** 70%+ of ecommerce traffic is mobile
- **Installation:** PWA can be installed to home screen without app store
- **Performance:** Service worker caching improves repeat visit load times

### Acceptance criteria
- [ ] Service worker for offline caching
- [ ] Web app manifest
- [ ] Install prompt
- [ ] Offline fallback page
- [ ] Lighthouse PWA score > 90

### Tasks
- [N] Create web app manifest (dynamic per store)
- [N] Create service worker (cache static assets, API responses, offline fallback)
- [N] Add install prompt component
- [N] Performance testing (Lighthouse)

---

### Polish Plan (Phases A-G): Make the Platform Shippable ✅
**Priority:** Critical | **Estimated effort:** Large
**Status:** Complete

After Phase 1 features were implemented, a comprehensive polish plan was executed to transform the
platform from having breadth (30+ API routers) into a fully functional, demo-able product. See
[POLISH_PLAN.md](POLISH_PLAN.md) for full details.

**Phases completed:**
- **Phase A: Checkout Flow** — Extended checkout with shipping address, discount codes, tax calculation, gift cards. Multi-section checkout page in storefront.
- **Phase B: Customer Accounts** — Full customer auth system (register/login/JWT), order history, wishlist, saved addresses. 8 storefront account pages.
- **Phase C: Dashboard Unified Shell** — Top bar with breadcrumbs + store switcher, dual-mode sidebar (platform/store), consistent layout across all 34 pages.
- **Phase D: Stub Pages** — All 11 sidebar stubs replaced with working CRUD pages (gift cards, upsells, refunds, segments, A/B tests, email, bulk, fraud, tax, currency, webhooks).
- **Phase E: Storefront Polish** — Mobile hamburger menu, multi-column footer, policy pages, toast on add-to-cart, stock indicators.
- **Phase F: Fulfillment & Tracking** — Order tracking fields, dashboard fulfillment workflow (ship → deliver), email notifications on fulfillment events.
- **Phase G: Seed Data** — Comprehensive seed script (8 products, 6 categories, 4 orders, 12 reviews, customer accounts). 36 e2e seed data tests.

**Bug fixes during polish:**
- Slug toggling on update (stores, products, categories)
- Paginated response unwrapping in dashboard pages
- Decimal string serialization in frontend
- Seed data idempotency

---

### Phase 2 Polish: Theme Engine v2, Animations & Platform Enhancements ✅
**Priority:** High | **Estimated effort:** Large
**Status:** Complete (all 5 phases)

After the Polish Plan (A-G), a second round of enhancements transformed the platform from
functional MVP to premium-feeling product. See [POLISH_PLAN.md](POLISH_PLAN.md) for full details.

**Phases completed:**
- **Phase 2.1: Theme Engine v2** — 5 new block types (product carousel, testimonials, countdown, video, trust badges), hero product showcase mode, block config editor, 4 new preset themes (Coastal, Monochrome, Cyberpunk, Terracotta), enhanced typography controls. **11 presets, 13 block types total.**
- **Phase 2.2: Animation & Motion** — Motion primitives (FadeIn, StaggerChildren, SlideIn, ScaleIn, ScrollReveal), staggered grid animations on all listing pages, micro-interactions (add-to-cart pulse, cart badge bounce), loading skeletons, dashboard animated counters.
- **Phase 2.3: Storefront Visual** — Product card redesign (New/Sale badges, hover zoom, theme-aware styling), recently viewed products section, enhanced product detail page.
- **Phase 2.4: Dashboard Enhancements** — Store overview KPI dashboard (4 metric cards, recent orders, quick actions), platform home dashboard (aggregate metrics, store cards), command palette (Cmd+K), notification badges on sidebar, enhanced analytics (customer metrics, order status bar chart).
- **Phase 2.5: Data & QoL** — CSV export (orders, products, customers), order notes (internal memos), inventory alerts (low-stock warnings), seed script enhancements.

**Key metrics after Phase 2 Polish:**
- 329 backend tests passing
- 187+ e2e tests across 24 spec files
- 34 dashboard pages building cleanly
- 18 storefront pages building cleanly
- 13 Alembic migrations, 37+ DB tables
- 11 preset themes, 13 block types

---

### Feature 31: Kubernetes Deployment & CI/CD
**Priority:** Must have (but last) | **Estimated effort:** Large
**Status:** Not started (next up after Polish Plan)

### What we're building
Deploy the complete platform to the existing K8s cluster. CI/CD pipeline.

### Acceptance criteria
- [ ] All services deploy to K8s namespace `dropshipping`
- [ ] Backend reachable at `api.platform.com`
- [ ] Dashboard reachable at `dashboard.platform.com`
- [ ] Storefront with wildcard subdomain: `*.platform.com`
- [ ] PostgreSQL and Redis running (StatefulSet or managed)
- [ ] Celery worker + beat + Flower running
- [ ] Automation service deployed with its own workers and beat
- [ ] GitHub Actions: push to `main` triggers build → deploy
- [ ] TLS via cert-manager + Let's Encrypt
- [ ] HPA for backend + storefront

### Tasks
- [K] Create Dockerfiles for production (multi-stage builds)
- [K] Create namespace, secrets, configmaps
- [K] PostgreSQL StatefulSet + Service
- [K] Redis Deployment + Service
- [K] Backend Deployment + Service + Ingress
- [K] Celery Worker + Beat + Flower Deployments
- [K] Dashboard Deployment + Service + Ingress
- [K] Storefront Deployment + Service + Ingress (wildcard subdomain)
- [K] Automation Service Deployment + Workers + Beat
- [K] HPA for backend + storefront
- [K] GitHub Actions: build images, push to registry, kubectl apply

---

## Phase 2: Standalone SaaS Products (A1-A8) ✅

> **STATUS: COMPLETE.** All 8 automation features have been implemented as **independent, separately
> hostable SaaS products** in `services/`. Each product has its own FastAPI backend, Next.js dashboard,
> landing page, database, Stripe billing, user auth, and test suite. The original monolithic
> `automation/` service design was replaced with this more scalable architecture.
>
> **Key metrics:** 8 standalone services, ~543 feature tests, 152 platform integration tests,
> master landing page (7 components), platform integration (ServiceIntegration model, 8 API endpoints,
> 2 dashboard pages).
>
> See [SERVICES.md](SERVICES.md) for the full services architecture and [ARCHITECTURE.md](ARCHITECTURE.md)
> for how they integrate with the core platform.

---

## Feature A1: Product Research Automation
**Priority:** Critical | **Estimated effort:** Large | **Impact:** Platform's #1 differentiator — the core USP
**Service:** Automation (`automation/`) — standalone, extractable as separate product

### What we're building
Automated daily product research: pull trends from AliExpress, TikTok (Apify), Reddit (PRAW), Google Trends (pytrends). Score products with a weighted algorithm + AI analysis (Claude API). Present recommendations with one-click import. This is the heart of the platform's value proposition.

### Why this matters for dropshipping
- **#1 value proposition:** The master plan states: "Enable users to launch and scale dropshipping stores with minimal manual intervention through AI-powered automation"
- **Time savings:** Manual product research takes 4-8 hours/day — automation reduces this to minutes
- **Data-driven decisions:** AI scoring removes emotion from product selection
- **Trend detection:** Discover winning products before market saturation (TikTok + Google Trends signals)
- **Competitive moat:** This is what differentiates us from Shopify/WooCommerce — they don't do this

### Acceptance criteria
- [ ] Celery Beat triggers daily research for each active store (configurable: daily/weekly)
- [ ] Data pulled from 4+ sources in parallel (Celery group):
  - AliExpress trending products (Affiliate API)
  - TikTok trend monitoring (Apify scraper)
  - Reddit product subreddits (PRAW)
  - Google Trends emerging searches (pytrends)
- [ ] Products scored with weighted algorithm (social signals 40%, market signals 30%, competition 15%, SEO 10%, fundamentals 5%)
- [ ] Top 20-50 products analyzed by Claude API (score, recommendation, reasoning, marketing angle)
- [ ] Auto-import high-confidence products (score >= 80) as drafts
- [ ] Medium-confidence products (65-79) added to watchlist for manual review
- [ ] Results saved to `WatchlistItem` table (automation DB)
- [ ] Daily email report sent to store owner (summary + top opportunities)
- [ ] Dashboard: "Product Research" page showing daily results (table with scores, AI reasoning)
- [ ] Dashboard: one-click import from research results
- [ ] Dashboard: watchlist page with import/dismiss actions
- [ ] Dashboard: research settings (niche keywords, source preferences, frequency, auto-import threshold)
- [ ] Automation service fetches store data via core backend API (no direct DB access)

### Tasks
- [A] Create `WatchlistItem` model (automation service DB)
- [A] AliExpress research service (affiliate API — hot products, sales velocity tracking)
- [A] TikTok research service (Apify scraper — trending videos, product extraction with AI)
- [A] Reddit research service (PRAW — r/shutupandtakemymoney, r/INEEEEDIT, r/DidntKnowIWantedThat)
- [A] Google Trends service (pytrends — emerging trends, growth rate calculation)
- [A] Product scoring algorithm (weighted formula from master plan)
- [A] AI analysis service (Claude API — product viability, marketing angle, content suggestions)
- [A] Auto-import pipeline (high-score products → draft product creation via backend API)
- [A] Celery task: daily_product_research (per store, parallel source collection)
- [A] Celery task: run_all_stores_research (fan-out from Beat schedule)
- [A] Celery Beat schedule config (daily at 8 AM)
- [A] Research results API endpoints (`/api/v1/automation/stores/{store_id}/research`)
- [A] Internal HTTP client to fetch store/user data from core backend
- [A] Tests
- [N] Dashboard: research results page (table with scores, AI reasoning, import button)
- [N] Dashboard: watchlist page (import/dismiss/monitor)
- [N] Dashboard: research settings (niche keywords, sources, frequency, auto-import threshold)
- [N] Dashboard: configure API client to call automation service (port 8001)

---

## Feature A2: Automated Product Import + AI Content
**Priority:** Critical | **Estimated effort:** Medium | **Impact:** Workflow acceleration — turns research into live products in seconds
**Service:** Automation (`automation/`) — standalone, extractable as separate product

### What we're building
Import products from research results or manual URL with AI-generated title, description, SEO metadata, and optimized images. Automatic pricing calculation with configurable markup. Products created as drafts for owner review.

### Why this matters for dropshipping
- **Efficiency:** Manual product listing takes 30-60 minutes per product — AI reduces this to seconds
- **Quality:** AI-generated descriptions are optimized for SEO and conversion (not copy-pasted from AliExpress)
- **Scale:** Enables merchants to list 100+ products per day
- **Pricing intelligence:** Auto-calculated pricing with psychological rounding (e.g., $29.99 not $30)
- **Image optimization:** Downloaded from supplier, converted to WebP, resized — faster store loading

### Acceptance criteria
- [ ] One-click import from research results (Feature A1)
- [ ] Manual import via supplier URL (paste AliExpress/CJ link)
- [ ] AI generates: SEO title, product description (3-4 paragraphs), meta description, keywords
- [ ] Images downloaded from source, optimized (WebP, resized), uploaded to storage
- [ ] Pricing auto-calculated (configurable markup multiplier, psychological pricing)
- [ ] Supplier link stored on product (supplier_url, supplier_product_id, supplier_cost)
- [ ] Product created as draft via core backend API (user reviews before publishing)
- [ ] Variant generation from supplier data (sizes, colors)
- [ ] Celery task handles the full pipeline (retries on failure)
- [ ] Dashboard: import progress indicator (real-time status)
- [ ] Dashboard: review imported product before publishing
- [ ] Dashboard: import settings (default markup, auto-publish toggle, content style)

### Tasks
- [A] Import service (orchestrates the full pipeline)
- [A] AI content generation service (Claude API prompts for product copy, SEO, marketing angle)
- [A] Image download + optimization service (Pillow: WebP, resize, quality)
- [A] Pricing calculation utility (markup multiplier, competitor pricing, psychological rounding)
- [A] Supplier data extraction service (parse AliExpress/CJ product pages for details, variants, images)
- [A] Celery task: import_product (chain of steps with retry)
- [A] API endpoint: `POST /api/v1/automation/stores/{store_id}/products/import`
- [A] API endpoint: `POST /api/v1/automation/stores/{store_id}/products/import-url` (manual URL)
- [A] Internal HTTP client to create products via core backend API
- [A] Tests
- [N] Dashboard: import progress indicator (WebSocket or polling)
- [N] Dashboard: review imported product (edit AI-generated content before publishing)
- [N] Dashboard: import settings page (markup, auto-publish, content style/tone)

---

## Feature A3: SEO Automation
**Priority:** High | **Estimated effort:** Medium | **Impact:** Free organic traffic — compounds over time
**Service:** Automation (`automation/`) — standalone, extractable as separate product

### What we're building
Automated SEO: sitemaps, schema markup, meta tags, keyword research, and AI-generated blog posts targeting keyword gaps. Weekly Celery task optimizes SEO across the store.

### Why this matters for dropshipping
- **Free traffic:** SEO is the only sustainable free traffic source — reduces dependency on paid ads
- **Blog content:** AI-generated posts drive long-tail keyword traffic (e.g., "best kitchen gadgets 2026")
- **Schema markup:** Product schema (star ratings, price, availability) in Google search results = higher CTR
- **Competitive advantage:** Most dropshippers ignore SEO — automated SEO gives a significant edge
- **Compounds over time:** SEO improvements accumulate — early investment pays dividends for months

### Acceptance criteria
- [ ] Auto-generated sitemap.xml for each store (products + categories + blog posts)
- [ ] JSON-LD schema markup on product pages (Product, AggregateRating, Offer)
- [ ] Keyword research automation (identify gaps and opportunities per niche)
- [ ] AI-generated blog posts targeting keyword gaps (weekly Celery task, 2-3 posts)
- [ ] Existing product SEO optimization (update titles, descriptions for better keywords)
- [ ] Internal linking suggestions between products and blog posts
- [ ] Dashboard: SEO overview page (scores, suggestions, keyword rankings)
- [ ] Blog posts display on storefront at `/blog/{slug}`
- [ ] Blog posts stored in automation service DB, served via automation API
- [ ] Search engine submission (Google, Bing)

### Tasks
- [A] Create `BlogPost` model (automation service DB)
- [A] Sitemap generation service (fetches product + category list from core backend API)
- [A] Schema markup generation service (Product, AggregateRating, BreadcrumbList)
- [A] Keyword research service (SerpAPI or free alternatives)
- [A] Content gap analysis service (find keyword opportunities)
- [A] AI blog post generation (Claude API — SEO-optimized, niche-relevant)
- [A] Product SEO optimization service (improve titles, meta descriptions)
- [A] Internal linking service (suggest links between content)
- [A] Celery task: weekly_seo_optimization (keyword research → blog posts → product SEO → sitemap → submit)
- [A] Public blog API endpoints (`/api/v1/automation/public/stores/{slug}/blog`)
- [A] Tests
- [N] Storefront: sitemap.xml route (calls automation service API)
- [N] Storefront: JSON-LD on product pages
- [N] Storefront: blog listing + detail pages (data from automation API)
- [N] Dashboard: SEO overview page (scores, suggestions)
- [N] Dashboard: blog post list with edit/delete

---

## Feature A4: Marketing Email Automation
**Priority:** High | **Estimated effort:** Large | **Impact:** Customer retention and abandoned cart recovery
**Service:** Automation (`automation/`) — standalone, extractable as separate product

### What we're building
Automated email marketing flows: abandoned cart recovery, post-purchase sequences, welcome series, win-back campaigns, and newsletter broadcasting. Via SendGrid. Distinct from transactional emails (Feature 11).

### Why this matters for dropshipping
- **Abandoned cart recovery:** Recovers 5-15% of abandoned carts — direct revenue with no ad spend
- **Long shipping buffer:** Post-purchase sequences keep customers engaged during 7-21 day shipping
- **Repeat purchases:** Win-back and cross-sell emails increase lifetime value
- **Email ROI:** $36 return for every $1 spent (Litmus) — cheapest marketing channel
- **Review collection:** Automated review request emails (ties into Feature 12)

### Acceptance criteria
- [ ] Abandoned cart email flow (1hr, 24hr, 72hr after cart abandonment)
- [ ] Post-purchase follow-up flow (order update → shipping tips → review request → cross-sell)
- [ ] Welcome series for new customers (3-email sequence with store introduction + first-order discount)
- [ ] Win-back campaign for lapsed customers (configurable inactivity period)
- [ ] Newsletter/broadcast sending to customer segments
- [ ] Visual flow builder (trigger → delay → send email → condition → branch)
- [ ] Email templates with drag-and-drop editor
- [ ] Unsubscribe management (one-click unsubscribe, CAN-SPAM compliance)
- [ ] Email analytics: sent, delivered, opened, clicked, unsubscribed, revenue attributed
- [ ] A/B testing for subject lines
- [ ] Dashboard: email flow builder page
- [ ] Dashboard: email campaign list with metrics
- [ ] Dashboard: email template editor

### Tasks
- [A] Create `EmailFlow` model (id, store_id, name, trigger_type, status, steps[JSON])
- [A] Create `EmailCampaign` model (id, store_id, name, segment_id, template_id, status, sent_count, open_count, click_count)
- [A] Create `EmailEvent` model (id, flow_id, campaign_id, customer_email, event_type, created_at)
- [A] Create `EmailUnsubscribe` model (id, store_id, email, reason, created_at)
- [A] Alembic migration
- [A] Flow engine (trigger evaluation, step execution, delay scheduling, branching)
- [A] Abandoned cart detection (listens for cart events via Redis pub/sub from core backend)
- [A] SendGrid integration (send, track delivery/opens/clicks)
- [A] Unsubscribe service (CAN-SPAM compliant one-click unsubscribe)
- [A] Celery tasks: evaluate_flow_triggers, execute_flow_step, send_broadcast
- [A] Email flow CRUD API endpoints
- [A] Email analytics API endpoints
- [A] Tests
- [N] Dashboard: visual email flow builder (drag-and-drop)
- [N] Dashboard: email template editor (WYSIWYG)
- [N] Dashboard: email campaign list with metrics
- [N] Dashboard: flow performance dashboard (conversion funnel)
- [N] Storefront: one-click unsubscribe page

---

## Feature A5: Competitor Monitoring
**Priority:** High | **Estimated effort:** Medium | **Impact:** Market intelligence — know what competitors are selling
**Service:** Automation (`automation/`) — standalone, extractable as separate product

### What we're building
Automated competitor store monitoring: discover competitor stores in the same niche, track their new product additions, reverse-engineer their suppliers, and alert store owners to opportunities. From the master plan's Product Research section.

### Why this matters for dropshipping
- **Validated products:** If a competitor is selling it, they've already tested market demand
- **Supplier discovery:** Reverse image search + AI matching to find the AliExpress source
- **Pricing intelligence:** Know what competitors charge for the same products
- **Speed advantage:** Get alerts when competitors add new products — import before market saturates
- **Master plan alignment:** Competitor monitoring is a core research source (Section 5 of master plan)

### Acceptance criteria
- [ ] Store owner can add competitor store URLs to monitor
- [ ] Auto-discover competitor stores in the same niche (via search)
- [ ] Daily scraping of competitor product catalogs
- [ ] Detect newly added products (compared to last scan)
- [ ] Reverse-engineer supplier source (reverse image search, AI matching)
- [ ] Competitor pricing tracking (price changes over time)
- [ ] Alert store owner when competitors add new high-potential products
- [ ] One-click import of competitor-discovered products
- [ ] Dashboard: competitor list (add/remove monitored competitors)
- [ ] Dashboard: competitor product feed (new additions, price changes)
- [ ] Dashboard: competitor performance comparison

### Tasks
- [A] Create `Competitor` model (id, store_id, name, url, last_scraped)
- [A] Create `CompetitorProduct` model (id, competitor_id, title, price, image_url, product_url, source_product, first_seen, price_history)
- [A] Competitor discovery service (find stores in same niche via search)
- [A] Competitor scraping service (Playwright/Scrapy — extract product catalog)
- [A] Reverse source finding service (reverse image search, title search on AliExpress, AI matching)
- [A] Price tracking service (detect changes over time)
- [A] Celery task: daily_competitor_scan (per monitored competitor)
- [A] Competitor API endpoints
- [A] Tests
- [N] Dashboard: competitor management page (add URL, view catalog)
- [N] Dashboard: competitor product feed (new items, price changes)
- [N] Dashboard: import from competitor discoveries

---

## Feature A6: Social Media Automation
**Priority:** High | **Estimated effort:** Medium | **Impact:** Marketing automation — auto-promote products on social platforms
**Service:** Automation (`automation/`) — standalone, extractable as separate product

### What we're building
Auto-post new products to social media (Instagram, Facebook, TikTok). AI-generated captions, hashtags, and scheduled posting. From Phase 3 of the master plan.

### Why this matters for dropshipping
- **Free marketing:** Social media posts reach followers without ad spend
- **New product promotion:** Auto-posting when products are imported saves hours of manual work
- **Engagement:** Regular posting keeps the brand visible
- **TikTok:** The #1 product discovery platform for dropshipping
- **Master plan alignment:** Phase 3 includes social media automation

### Acceptance criteria
- [ ] Auto-generate social media content when new product is published
- [ ] AI-generated captions, hashtags (platform-specific)
- [ ] Instagram: post product image with caption + hashtags
- [ ] Facebook: share product with link and description
- [ ] TikTok: generate video ideas and script suggestions (manual creation queue)
- [ ] Scheduled posting (configure posting times per platform)
- [ ] Social media account linking (OAuth for Meta, TikTok)
- [ ] Dashboard: social media settings (linked accounts, posting schedule)
- [ ] Dashboard: social content queue (pending, scheduled, posted)
- [ ] Dashboard: social media performance metrics (reach, engagement)

### Tasks
- [A] Social content generation service (Claude API — platform-specific captions, hashtags)
- [A] Meta Graph API integration (Instagram + Facebook posting)
- [A] TikTok content suggestions service (video ideas, script generation — not auto-posting)
- [A] Create `SocialPost` model (id, store_id, platform, content, image_url, status, scheduled_for, posted_at, engagement_metrics)
- [A] Alembic migration
- [A] Celery task: schedule_social_posts (trigger on product publish)
- [A] Celery task: post_to_social (execute scheduled posts)
- [A] Social media API endpoints
- [A] Tests
- [N] Dashboard: social media account linking
- [N] Dashboard: social content queue (scheduled, posted, failed)
- [N] Dashboard: social post preview and editor
- [N] Dashboard: engagement metrics

---

## Feature A7: Ad Campaign Management
**Priority:** Medium | **Estimated effort:** Large | **Impact:** Paid acquisition automation — scale profitable campaigns
**Service:** Automation (`automation/`) — standalone, extractable as separate product

### What we're building
Google Ads and Meta Ads (Facebook/Instagram) campaign automation. Auto-create campaigns for new products, manage budgets, track ROAS. From Phase 3 of the master plan.

### Why this matters for dropshipping
- **Primary traffic source:** Paid ads are how most dropshippers get customers initially
- **Automation value:** Creating ad campaigns manually for each product is time-consuming
- **ROAS tracking:** Understanding return on ad spend per product is critical for profitability
- **Budget optimization:** Auto-pause underperforming campaigns, scale winning ones
- **Master plan alignment:** Phase 3 explicitly includes ad campaign management

### Acceptance criteria
- [ ] Google Ads API integration (campaign creation, keyword targeting, budget management)
- [ ] Meta Ads API integration (Facebook + Instagram ad creation, audience targeting)
- [ ] Auto-create ad campaign when product is published (configurable)
- [ ] AI-generated ad copy and creative suggestions (Claude API)
- [ ] Budget management: daily/lifetime budget per campaign
- [ ] Performance tracking: impressions, clicks, conversions, ROAS per campaign and product
- [ ] Auto-optimization: pause campaigns below ROAS threshold, scale profitable ones
- [ ] Dashboard: ad campaign management page (create, edit, pause, delete)
- [ ] Dashboard: ad performance dashboard (ROAS, CPA, spend by product)
- [ ] Dashboard: ad account linking (Google, Meta OAuth)
- [ ] Dashboard: ad budget settings (default budget, auto-scale rules)

### Tasks
- [A] Google Ads API integration (campaign CRUD, keyword management, conversion tracking)
- [A] Meta Business API integration (campaign CRUD, audience creation, pixel tracking)
- [A] AI ad copy generation service (Claude API — ad headlines, descriptions, CTA)
- [A] Create `AdCampaign` model (id, store_id, platform, product_id, status, budget, spend, impressions, clicks, conversions, revenue, roas)
- [A] Create `AdAccount` model (id, store_id, platform, credentials, status)
- [A] Alembic migration
- [A] Campaign auto-creation service (trigger on product publish)
- [A] Performance tracking service (poll APIs for metrics)
- [A] Auto-optimization service (pause/scale based on ROAS rules)
- [A] Celery task: sync_ad_performance (hourly metrics pull)
- [A] Celery task: optimize_campaigns (daily auto-pause/scale)
- [A] Ad management API endpoints
- [A] Tests
- [N] Dashboard: ad account linking (OAuth flow)
- [N] Dashboard: campaign management page
- [N] Dashboard: ad performance dashboard (charts, ROAS table)
- [N] Dashboard: auto-optimization settings

---

## Feature A8: AI Shopping Assistant
**Priority:** Low | **Estimated effort:** Large | **Impact:** Customer experience and conversion

### What we're building
AI-powered chatbot on the storefront that helps customers find products, answers questions, and guides purchases. Powered by Claude API with store-specific product knowledge.

### Why this matters for dropshipping
- **Conversion:** AI assistants can increase conversion by 10-30%
- **Support:** Handles common questions (shipping times, return policy) 24/7
- **Shipping questions:** The #1 question on dropshipping stores is "how long will shipping take?" — AI can answer automatically
- **Product discovery:** Natural language search ("I need a gift for my mom") outperforms keyword search

### Acceptance criteria
- [ ] Chat widget on storefront (floating button, expandable chat)
- [ ] Natural language product search
- [ ] Answer questions about store policies (shipping times, returns)
- [ ] Product recommendations in chat
- [ ] Store-specific knowledge (products, policies injected into context)
- [ ] Dashboard: chatbot settings (enable/disable, personality)
- [ ] Dashboard: conversation log and analytics

### Tasks
- [P] AI chat service (Claude API with store context injection)
- [P] Product search tool for AI (function calling)
- [P] Store policy knowledge base
- [P] Create `ChatConversation` model
- [P] Chat API endpoint (streaming via SSE)
- [P] Tests
- [N] Storefront: chat widget component
- [N] Dashboard: chatbot settings and conversation log

---

## Future Features (Backlog — Not Scheduled)

These are ideas for potential future development beyond the numbered features above.

| Feature                        | Description                                                        |
| ------------------------------ | ------------------------------------------------------------------ |
| Mobile admin app               | React Native dashboard for managing stores on the go               |
| TikTok trend scraping          | Dedicated Apify-based TikTok product discovery (extends A1)        |
| Social commerce (shops)        | Facebook/Instagram Shop, Google Shopping, TikTok Shop catalog sync |
| Blog & CMS                     | Built-in blog with WYSIWYG editor for content marketing            |
| Loyalty & rewards program      | Points-based loyalty with VIP tiers                                |
| Referral program               | Users earn credits for referring new platform users                |
| White-label / platform resale  | Remove platform branding for Enterprise plan                       |
| Headless commerce SDK          | JavaScript SDK for custom storefronts                              |
| Multi-storefront management    | Unified management of multiple stores from one view                |
| Print-on-demand integration    | Printful/Printify API for custom merchandise                      |
| Supplier marketplace           | Built-in supplier directory with reviews and auto-integration     |
| GDPR compliance toolkit        | Cookie consent, data export, right to deletion                    |
| Automated compliance pages     | AI-generated Terms, Privacy Policy, Shipping Policy               |
| Customer support ticketing     | Built-in help desk for customer inquiries                         |
| Product video generation       | AI-generated product videos from images for social media          |
| Subscription products          | Recurring product subscriptions (subscribe & save model)          |
| Live shopping / livestream     | Real-time product demos with buy-now overlay                      |

---

## Working Agreement

- **One feature at a time.** Finish and test locally before starting the next.
- **Tests are mandatory** for backend API endpoints.
- **No premature optimization.** Get it working, then improve.
- **Backend first, then frontend.** API is the source of truth.
- **Local dev only** until Feature 31 (K8s deployment).
- **Impact-ordered.** We build what drives the most revenue, conversion, and automation value first.
- **Dropshipping-first.** Every feature is designed for the dropshipping model — no generic ecommerce bloat.
