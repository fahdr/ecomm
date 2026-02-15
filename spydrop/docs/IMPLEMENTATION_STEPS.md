# Implementation Steps

> Part of [SpyDrop](README.md) documentation

This document describes how SpyDrop was implemented, step by step, from initial scaffolding to fully functional service with 156 tests and 8 dashboard pages. It serves as both a historical record and a template for implementing similar services.

---

## Step 1: Template Scaffolding

SpyDrop was generated from the service template using the scaffold script (`scripts/create-service.sh`). The script replaced all `{{placeholders}}` with SpyDrop-specific values:

| Placeholder | Value |
|------------|-------|
| `{{SERVICE_NAME}}` | SpyDrop |
| `{{SERVICE_SLUG}}` | spydrop |
| `{{SERVICE_TAGLINE}}` | Competitor Intelligence |
| `{{BACKEND_PORT}}` | 8105 |
| `{{DASHBOARD_PORT}}` | 3105 |
| `{{LANDING_PORT}}` | 3205 |
| `{{DB_PORT}}` | 5505 |
| `{{REDIS_PORT}}` | 6405 |
| `{{PRIMARY_COLOR_OKLCH}}` | oklch(0.60 0.15 220) |
| `{{PRIMARY_COLOR_HEX}}` | #06b6d4 |
| `{{ACCENT_COLOR_OKLCH}}` | oklch(0.70 0.12 210) |
| `{{ACCENT_COLOR_HEX}}` | #67e8f9 |
| `{{HEADING_FONT}}` | Geist |
| `{{BODY_FONT}}` | Geist |

### Generated File Structure

```
spydrop/
+-- Makefile
+-- README.md
+-- docker-compose.yml
+-- backend/
|   +-- app/
|   |   +-- main.py, config.py, database.py
|   |   +-- api/ (auth, billing, api_keys, health, usage, webhooks, deps)
|   |   +-- models/ (base, user, subscription, api_key)
|   |   +-- schemas/ (auth, billing)
|   |   +-- services/ (auth_service, billing_service)
|   |   +-- constants/ (plans.py -- template limits)
|   |   +-- tasks/, utils/
|   +-- tests/ (conftest, test_auth, test_billing, test_api_keys, test_health)
|   +-- alembic/
+-- dashboard/
|   +-- src/
|   |   +-- service.config.ts
|   |   +-- app/ (page, billing, api-keys, settings, login, register)
|   |   +-- components/, lib/
+-- landing/
+-- scripts/
```

The template provided a working auth system, billing integration, API key management, and dashboard out of the box. The following steps added SpyDrop-specific domain features.

---

## Step 2: Domain Models

### 2a. Competitor Model (`backend/app/models/competitor.py`)

Created the `Competitor` model representing a monitored competitor store:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID (PK) | Unique identifier |
| `user_id` | UUID (FK -> users) | Owning user, indexed |
| `name` | String(255) | Human-readable store name |
| `url` | String(2048) | Competitor store URL |
| `platform` | String(50) | E-commerce platform (shopify, woocommerce, custom) |
| `last_scanned` | DateTime (nullable) | Most recent scan timestamp |
| `status` | String(20) | Monitoring status (active, paused, error) |
| `product_count` | Integer | Denormalized product count |
| `created_at` | DateTime | Record creation |
| `updated_at` | DateTime | Last modification |

Relationships: `products` (one-to-many), `scan_results` (one-to-many), `alerts` (one-to-many), `owner` (many-to-one User).

### 2b. CompetitorProduct Model (`backend/app/models/competitor.py`)

Created in the same file, representing a product discovered on a competitor's store:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID (PK) | Unique identifier |
| `competitor_id` | UUID (FK -> competitors) | Parent competitor, indexed |
| `title` | String(512) | Product name |
| `url` | String(2048) | Direct product page URL |
| `image_url` | String(2048, nullable) | Product image URL |
| `price` | Float (nullable) | Current price |
| `currency` | String(10) | Currency code (default USD) |
| `first_seen` | DateTime | First discovery timestamp |
| `last_seen` | DateTime | Last seen in a scan |
| `price_history` | JSON | List of `{date, price}` entries |
| `status` | String(20) | Availability (active, removed) |
| `created_at` | DateTime | Record creation |
| `updated_at` | DateTime | Last modification |

Relationships: `competitor` (many-to-one), `source_matches` (one-to-many), `alerts` (one-to-many).

### 2c. PriceAlert + AlertHistory Models (`backend/app/models/alert.py`)

**PriceAlert** -- a monitoring rule:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID (PK) | Unique identifier |
| `user_id` | UUID (FK -> users) | Owning user |
| `competitor_product_id` | UUID (FK, nullable) | Specific product to monitor |
| `competitor_id` | UUID (FK, nullable) | Monitor all products on this competitor |
| `alert_type` | String(50) | price_drop, price_increase, new_product, out_of_stock, back_in_stock |
| `threshold` | Float (nullable) | Percentage threshold for price alerts |
| `is_active` | Boolean | Whether the alert is active |
| `last_triggered` | DateTime (nullable) | When the alert last fired |
| `created_at` | DateTime | Record creation |

**AlertHistory** -- a triggered alert instance:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID (PK) | Unique identifier |
| `alert_id` | UUID (FK -> price_alerts) | Parent alert |
| `message` | String(1024) | Human-readable trigger description |
| `data` | JSON | Context data (old_price, new_price, etc.) |
| `created_at` | DateTime | When the alert triggered |

### 2d. ScanResult Model (`backend/app/models/scan.py`)

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID (PK) | Unique identifier |
| `competitor_id` | UUID (FK -> competitors) | Scanned competitor |
| `new_products_count` | Integer | Number of new products found |
| `removed_products_count` | Integer | Number of products removed |
| `price_changes_count` | Integer | Number of price changes detected |
| `scanned_at` | DateTime | When the scan ran |
| `duration_seconds` | Float (nullable) | Scan duration |

### 2e. SourceMatch Model (`backend/app/models/source_match.py`)

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID (PK) | Unique identifier |
| `competitor_product_id` | UUID (FK -> competitor_products) | Matched product |
| `supplier` | String(255) | Supplier name (AliExpress, DHgate, etc.) |
| `supplier_url` | String(2048) | Supplier product listing URL |
| `cost` | Float (nullable) | Supplier price |
| `currency` | String(10) | Currency code |
| `confidence_score` | Float | Match confidence (0.0 to 1.0) |
| `margin_percent` | Float (nullable) | Calculated profit margin |
| `created_at` | DateTime | Record creation |

### 2f. Model Registration

Updated `backend/app/models/__init__.py` to export all new models:

```python
from app.models.competitor import Competitor, CompetitorProduct
from app.models.alert import AlertHistory, PriceAlert
from app.models.scan import ScanResult
from app.models.source_match import SourceMatch
```

---

## Step 3: Plan Limits Configuration

Updated `backend/app/constants/plans.py` with SpyDrop-specific limits:

```python
PLAN_LIMITS = {
    PlanTier.free: PlanLimits(
        max_items=3,           # 3 competitors
        max_secondary=50,      # 50 products tracked
        price_monthly_cents=0,
        trial_days=0,
        api_access=False,
    ),
    PlanTier.pro: PlanLimits(
        max_items=25,          # 25 competitors
        max_secondary=2500,    # 2,500 products
        price_monthly_cents=2900,
        trial_days=14,
        api_access=True,
    ),
    PlanTier.enterprise: PlanLimits(
        max_items=-1,          # Unlimited
        max_secondary=-1,      # Unlimited
        price_monthly_cents=9900,
        trial_days=14,
        api_access=True,
    ),
}
```

---

## Step 4: Service Layer

### 4a. Competitor Service (`backend/app/services/competitor_service.py`)

Implemented 8 functions:

| Function | Purpose |
|----------|---------|
| `get_competitor_count(db, user_id)` | Count user's competitors |
| `check_plan_limit(db, user)` | Verify user can create another competitor |
| `create_competitor(db, user, name, url, platform)` | Create with plan limit check |
| `list_competitors(db, user_id, page, per_page)` | Paginated list by user |
| `get_competitor(db, user_id, competitor_id)` | Single competitor by ID |
| `update_competitor(db, user_id, competitor_id, ...)` | Partial update |
| `delete_competitor(db, user_id, competitor_id)` | Cascading delete |
| `list_competitor_products(db, user_id, competitor_id, page, per_page)` | Products for a competitor |
| `list_all_products(db, user_id, page, per_page, status_filter, sort_by)` | Cross-competitor product list |
| `get_product(db, user_id, product_id)` | Single product with owner verification |

### 4b. Scan Service (`backend/app/services/scan_service.py`)

Implemented mock scanning engine:

| Function | Purpose |
|----------|---------|
| `run_scan(db, competitor_id)` | Simulate scanning: add 0-3 new products, remove 0-1, change 0-2 prices |
| `list_scan_results(db, user_id, competitor_id?, page, per_page)` | Paginated scan history |
| `_generate_product_name()` | Generate realistic mock product names |
| `_generate_price()` | Generate realistic mock prices ($5-$200) |
| `_generate_image_url()` | Generate placeholder image URLs |

### 4c. Alert Service (`backend/app/services/alert_service.py`)

Implemented 7 functions:

| Function | Purpose |
|----------|---------|
| `create_alert(db, user_id, alert_type, ...)` | Create a monitoring rule |
| `list_alerts(db, user_id, page, per_page, is_active?)` | Paginated alert list |
| `get_alert(db, user_id, alert_id)` | Single alert by ID |
| `update_alert(db, user_id, alert_id, ...)` | Partial update (uses Ellipsis sentinel) |
| `delete_alert(db, user_id, alert_id)` | Delete alert + history |
| `list_alert_history(db, user_id, alert_id?, page, per_page)` | Triggered alert history |
| `check_alerts_for_scan(db, scan_result_id)` | Evaluate alerts against scan results |

### 4d. Source Service (`backend/app/services/source_service.py`)

Implemented mock supplier matching:

| Function | Purpose |
|----------|---------|
| `find_sources(db, product_id)` | Generate 1-4 mock supplier matches with confidence scores |
| `list_source_matches(db, product_id, page, per_page)` | Paginated source matches |

Mock suppliers: AliExpress, DHgate, 1688, Made-in-China, Global Sources, Alibaba, Banggood, LightInTheBox.

---

## Step 5: API Routes

### 5a. Competitor Routes (`backend/app/api/competitors.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/v1/competitors/` | create | Create competitor with plan limit check |
| `GET /api/v1/competitors/` | list | Paginated list for authenticated user |
| `GET /api/v1/competitors/{id}` | get | Single competitor detail |
| `PATCH /api/v1/competitors/{id}` | update | Partial update |
| `DELETE /api/v1/competitors/{id}` | delete | Cascading delete (204) |
| `GET /api/v1/competitors/{id}/products` | products | Paginated products sub-resource |

### 5b. Product Routes (`backend/app/api/products.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/products/` | list | Cross-competitor product list with filters and sorting |
| `GET /api/v1/products/{id}` | detail | Product with full price history |

### 5c. Schemas (`backend/app/schemas/competitor.py`)

Created Pydantic v2 schemas: `CompetitorCreate`, `CompetitorUpdate`, `CompetitorResponse`, `CompetitorListResponse`, `CompetitorProductResponse`, `CompetitorProductListResponse`.

### 5d. Router Registration

Updated `backend/app/api/__init__.py` and `backend/app/main.py` to include the competitors and products routers under the `/api/v1` prefix.

---

## Step 6: Backend Tests

### 6a. Competitor Tests (`backend/tests/test_competitors.py`)

17 tests covering the full CRUD lifecycle:

- Create: success, default platform, missing name (422), missing url (422), empty name (422), unauthenticated (401), plan limit enforcement (403 after 3 on free tier)
- List: empty, with data, pagination, user isolation
- Get: success, not found (404), invalid UUID (400), wrong user (404)
- Update: name, status, multiple fields, not found (404), wrong user (404)
- Delete: success (204), not found (404), wrong user (404), reduces count
- Products sub-resource: empty list, invalid ID (400)

### 6b. Product Tests (`backend/tests/test_products.py`)

12 tests covering product listing and detail:

- List: empty, after competitor created, unauthenticated (401), pagination params, invalid page (422), invalid per_page (422), sort_by options, status filter, user isolation
- Detail: not found (404), invalid ID (400), unauthenticated (401)
- Seeded data: list with 5 products, detail with price history (4 entries), wrong user (404), active/removed filter, sort by price ascending

### 6c. Total Test Count

| File | Count |
|------|-------|
| test_auth.py | 11 |
| test_competitors.py | 17 |
| test_products.py | 12 |
| test_billing.py | 9 |
| test_api_keys.py | 5 |
| test_health.py | 1 |
| **Total** | **43** |

---

## Step 7: Dashboard Pages

### 7a. Service Configuration (`dashboard/src/service.config.ts`)

Updated the config with SpyDrop branding:

- **Name:** SpyDrop
- **Tagline:** Competitor Intelligence
- **Colors:** Slate Cyan primary, Light Cyan accent
- **Fonts:** Geist for heading and body
- **Navigation:** Dashboard, Competitors, Products, Alerts, Sources, Scans, API Keys, Billing, Settings
- **Plans:** Free ($0/3 competitors), Pro ($29/25), Enterprise ($99/unlimited)

### 7b. Competitors Page (`dashboard/src/app/competitors/page.tsx`)

Full-featured competitor management page:
- Summary cards (total, active monitoring, total products tracked)
- Competitor table with status badges, platform tags, product counts, last scanned timestamps
- Add Competitor dialog with name, URL, and platform fields
- Inline pause/resume toggle per competitor
- Delete confirmation dialog with cascading delete warning
- Pagination controls
- Loading skeletons and error state handling
- Motion animations (PageTransition, FadeIn, StaggerChildren)

### 7c. Products Page (`dashboard/src/app/products/page.tsx`)

Cross-competitor product browsing:
- Summary cards (total products, price drops, price increases, active products)
- Status filter buttons (All, Active, Removed)
- Sort dropdown (Last Seen, First Seen, Price, Title)
- Product card grid with price change badges (up/down/stable)
- Mini price history bar chart on each card
- Price History dialog with full timeline, lowest/highest/data points summary
- Pagination controls
- Loading skeletons and error/empty state handling

### 7d. Other Pages (from template)

- **Dashboard Home** (`/`): KPI cards, usage progress bar, quick action links
- **Billing** (`/billing`): Plan cards, checkout, subscription management
- **API Keys** (`/api-keys`): Create, list, revoke
- **Settings** (`/settings`): User profile settings
- **Login** (`/login`): Email/password login form
- **Register** (`/register`): Registration form

---

## Step 8: Landing Page

The landing page at `spydrop/landing/` is a static Next.js site with:
- Hero section introducing SpyDrop's Competitor Intelligence tagline
- Feature highlights (monitoring, tracking, alerts, source finding)
- Pricing table matching the plan tiers
- Call-to-action buttons linking to the dashboard registration

---

## Summary

| Step | What Was Done | Files Created/Modified |
|------|--------------|----------------------|
| 1 | Template scaffolding | Entire service directory structure |
| 2 | Domain models | `competitor.py`, `alert.py`, `scan.py`, `source_match.py`, `__init__.py` |
| 3 | Plan limits | `plans.py` (updated limits) |
| 4 | Service layer | `competitor_service.py`, `scan_service.py`, `alert_service.py`, `source_service.py` |
| 5 | API routes | `competitors.py`, `products.py`, `competitor.py` (schemas), `__init__.py`, `main.py` |
| 6 | Tests | `test_competitors.py` (17), `test_products.py` (12) |
| 7 | Dashboard pages | `service.config.ts`, `competitors/page.tsx`, `products/page.tsx` |
| 8 | Landing page | `landing/` directory |

---

*See also: [README](README.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md) · [Project Manager](PROJECT_MANAGER.md)*
