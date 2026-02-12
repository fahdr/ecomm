# QA Engineer Guide

**For QA Engineers:** This guide covers the test infrastructure, how to run tests, what coverage exists, and how to manually verify SpyDrop features. SpyDrop is a Competitor Intelligence service with competitor CRUD, product catalog tracking with price history, alert configuration, scan scheduling, reverse source finding, and plan limit enforcement.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| pytest | Test runner and assertions |
| pytest-asyncio | Async test support for FastAPI endpoints |
| httpx `AsyncClient` | In-process HTTP client (no server needed) |
| SQLAlchemy 2.0 async | Direct database access for seeding test data |
| PostgreSQL 16 | Real database (not SQLite) for production-accurate testing |

---

## Running Tests

### All 43 Backend Tests

```bash
# From /workspaces/ecomm/services/spydrop/
make test-backend

# Or directly:
cd /workspaces/ecomm/services/spydrop/backend
pytest -v
```

### Run a Specific Test File

```bash
cd /workspaces/ecomm/services/spydrop/backend
pytest tests/test_competitors.py -v
pytest tests/test_products.py -v
pytest tests/test_auth.py -v
pytest tests/test_billing.py -v
pytest tests/test_api_keys.py -v
pytest tests/test_health.py -v
```

### Run a Single Test

```bash
cd /workspaces/ecomm/services/spydrop/backend
pytest tests/test_competitors.py::test_create_competitor_plan_limit_free_tier -v
```

---

## Coverage Table

| Test File | Test Count | Coverage Areas |
|-----------|-----------|----------------|
| `test_auth.py` | 11 | Registration (success, duplicate email, short password), login (success, wrong password, nonexistent user), token refresh (valid, invalid), profile retrieval (authenticated, unauthenticated) |
| `test_competitors.py` | 17 | Create (success, default platform, missing name/url/empty name, unauthenticated, plan limit), list (empty, with data, pagination, user isolation), get single (success, not found, invalid ID, wrong user), update (name, status, multiple fields, not found, wrong user), delete (success, not found, wrong user, reduces count), competitor products (empty, invalid ID) |
| `test_products.py` | 12 | List all (empty, after competitor, unauthenticated, pagination params, invalid page/per_page, sort_by, status filter, user isolation), product detail (not found, invalid ID, unauthenticated), seeded data (list with products, detail with price history, wrong user, status filter active/removed, sort by price) |
| `test_billing.py` | 9 | List plans (returns 3 tiers, has pricing), checkout (pro plan, free plan fails, duplicate subscription fails), billing overview (free plan, after subscribe), current subscription (none, after subscribe) |
| `test_api_keys.py` | 5 | Create key (returns raw key), list keys (no raw key exposed), revoke key (marks inactive), auth via API key (X-API-Key header), invalid API key (returns 401) |
| `test_health.py` | 1 | Health check returns 200 with service name, status "ok", and timestamp |
| **Total** | **43** | |

---

## Test Structure

### Fixtures (from `conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Single asyncio event loop for all tests |
| `setup_db` | function (autouse) | Creates tables before each test, truncates all with CASCADE after |
| `db` | function | Async SQLAlchemy session for direct database operations |
| `client` | function | httpx `AsyncClient` configured for the FastAPI app |
| `auth_headers` | function | Pre-registered user with `Authorization: Bearer <token>` headers |

### Helper Functions

| Function | Location | Description |
|----------|----------|-------------|
| `register_and_login(client, email?)` | `conftest.py` | Registers a user and returns auth headers dict |
| `create_competitor_via_api(client, headers, name?, url?, platform?)` | `test_competitors.py` | Creates a competitor via POST and returns response JSON |
| `seed_competitor_with_products(db, user_id, name?, count?, status?)` | `test_products.py` | Seeds a competitor with products directly in the database |

### Key Testing Patterns

1. **User isolation:** Tests create multiple users and verify that resources are scoped to each user. Accessing another user's resource returns 404 (not 403).
2. **Plan limit enforcement:** Tests create resources up to the free-tier limit (3 competitors) and verify the next creation returns 403.
3. **Database seeding:** For complex test scenarios (products with price history), data is seeded directly via the SQLAlchemy session rather than through the API.
4. **Mock Stripe mode:** All billing tests run with empty `STRIPE_SECRET_KEY`, so subscription creation happens directly in the database.
5. **Table truncation:** Every test starts with clean tables via `TRUNCATE CASCADE`. Non-self DB connections are terminated first to prevent deadlocks.

---

## API Documentation

Interactive Swagger docs are available at **http://localhost:8105/docs** when the backend is running (port 8105).

### API Response Format

**Paginated lists:**
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

**Single resource:**
```json
{
  "id": "uuid-string",
  "field": "value",
  "created_at": "2026-02-12T10:00:00Z",
  "updated_at": "2026-02-12T10:00:00Z"
}
```

**Error response:**
```json
{
  "detail": "Human-readable error message"
}
```

**Token response (auth):**
```json
{
  "access_token": "jwt-string",
  "refresh_token": "jwt-string",
  "token_type": "bearer"
}
```

---

## Endpoint Summary

### Auth (`/api/v1/auth/`)

| Method | Path | Auth | Status Codes | Notes |
|--------|------|------|-------------|-------|
| POST | `/register` | None | 201, 409, 422 | Returns tokens; 409 if email exists; 422 if password < 8 chars |
| POST | `/login` | None | 200, 401 | Returns tokens; 401 if bad credentials |
| POST | `/refresh` | None | 200, 401 | Accepts refresh_token; 401 if invalid/expired |
| GET | `/me` | Bearer | 200, 401 | Returns user profile (email, plan, is_active) |
| POST | `/forgot-password` | None | 200 | Always returns success (prevents email enumeration) |
| POST | `/provision` | Bearer/API Key | 201 | Creates user + API key for platform integration |

### Competitors (`/api/v1/competitors/`)

| Method | Path | Auth | Status Codes | Notes |
|--------|------|------|-------------|-------|
| POST | `/` | Bearer | 201, 403, 422 | Creates competitor; 403 if plan limit reached |
| GET | `/` | Bearer | 200 | Paginated list (`?page=1&per_page=20`) |
| GET | `/{id}` | Bearer | 200, 400, 404 | Single competitor; 400 if invalid UUID |
| PATCH | `/{id}` | Bearer | 200, 400, 404 | Partial update (name, url, platform, status) |
| DELETE | `/{id}` | Bearer | 204, 400, 404 | Cascading delete (products, scans, alerts, sources) |
| GET | `/{id}/products` | Bearer | 200, 400 | Paginated products for specific competitor |

### Products (`/api/v1/products/`)

| Method | Path | Auth | Status Codes | Notes |
|--------|------|------|-------------|-------|
| GET | `/` | Bearer | 200, 401, 422 | Cross-competitor list; filters: `?status=active&sort_by=price` |
| GET | `/{id}` | Bearer | 200, 400, 404 | Product detail with full `price_history` array |

### Alerts (planned: `/api/v1/alerts/`)

| Method | Path | Auth | Status Codes | Notes |
|--------|------|------|-------------|-------|
| POST | `/` | Bearer | 201 | Create alert (alert_type, threshold, competitor_id or product_id) |
| GET | `/` | Bearer | 200 | Paginated list with `?is_active=true` filter |
| GET | `/{id}` | Bearer | 200, 404 | Single alert details |
| PATCH | `/{id}` | Bearer | 200, 404 | Update alert_type, threshold, is_active |
| DELETE | `/{id}` | Bearer | 204, 404 | Delete alert + history |

### Billing (`/api/v1/billing/`)

| Method | Path | Auth | Status Codes | Notes |
|--------|------|------|-------------|-------|
| GET | `/plans` | None | 200 | Public; returns 3 tiers (free, pro, enterprise) |
| POST | `/checkout` | Bearer | 201, 400 | Creates checkout session; 400 if free plan or already subscribed |
| POST | `/portal` | Bearer | 200, 400 | Creates Stripe customer portal URL |
| GET | `/current` | Bearer | 200 | Returns current subscription or null |
| GET | `/overview` | Bearer | 200 | Full billing overview with plan, subscription, and usage |

### API Keys (`/api/v1/api-keys`)

| Method | Path | Auth | Status Codes | Notes |
|--------|------|------|-------------|-------|
| POST | `` | Bearer | 201 | Creates key; raw key returned ONLY in response |
| GET | `` | Bearer | 200 | Lists keys (no raw key, only key_prefix) |
| DELETE | `/{id}` | Bearer | 204, 404 | Revokes key (marks inactive, not deleted) |

### Other

| Method | Path | Auth | Status Codes | Notes |
|--------|------|------|-------------|-------|
| GET | `/api/v1/health` | None | 200 | Returns `{ service, status, timestamp }` |
| GET | `/api/v1/usage` | Bearer/API Key | 200 | Usage metrics for cross-service integration |
| POST | `/api/v1/webhooks/stripe` | Stripe sig | 200, 400 | Handles subscription lifecycle events |

---

## Verification Checklist

### Authentication Flow
- [ ] Register with valid email/password -> 201 with tokens
- [ ] Register with existing email -> 409
- [ ] Register with password < 8 chars -> 422
- [ ] Login with valid credentials -> 200 with tokens
- [ ] Login with wrong password -> 401
- [ ] Login with nonexistent email -> 401
- [ ] Refresh with valid refresh token -> 200 with new tokens
- [ ] Refresh with access token (not refresh) -> 401
- [ ] GET /me with valid token -> 200 with user profile
- [ ] GET /me without token -> 401

### Competitor Management
- [ ] Create competitor with name + URL -> 201 with status "active", product_count 0
- [ ] Create without name -> 422
- [ ] Create without URL -> 422
- [ ] Create without auth -> 401
- [ ] Create 4th competitor on free plan -> 403 with plan limit message
- [ ] List competitors -> paginated response with correct total
- [ ] List with pagination params -> correct page/per_page in response
- [ ] Get single competitor by UUID -> 200 with all fields
- [ ] Get with invalid UUID -> 400
- [ ] Get nonexistent UUID -> 404
- [ ] Get another user's competitor -> 404 (not 403)
- [ ] PATCH update name only -> name changes, other fields unchanged
- [ ] PATCH update status to "paused" -> status changes
- [ ] PATCH multiple fields at once -> all provided fields change
- [ ] DELETE competitor -> 204, subsequent GET returns 404
- [ ] DELETE cascades products, scans, alerts, source matches

### Product Tracking
- [ ] List products for user with no competitors -> empty list, total 0
- [ ] List products after seeding -> correct total and items
- [ ] Filter by `?status=active` -> only active products returned
- [ ] Filter by `?status=removed` -> only removed products returned
- [ ] Sort by `?sort_by=price` -> ascending price order
- [ ] Sort by `?sort_by=title` -> alphabetical order
- [ ] Product detail includes `price_history` array
- [ ] Product detail includes `competitor_name`
- [ ] Products from user A invisible to user B

### Billing
- [ ] GET /plans -> 3 tiers (free: $0, pro: $29, enterprise: $99)
- [ ] Checkout pro plan -> 201 with checkout_url and session_id
- [ ] Checkout free plan -> 400
- [ ] Checkout with existing subscription -> 400
- [ ] Overview shows current plan and usage metrics
- [ ] Overview reflects upgraded plan after checkout

### API Keys
- [ ] Create key -> raw key in response, key_prefix matches
- [ ] List keys -> no raw key exposed, key_prefix present
- [ ] Revoke key -> key becomes inactive
- [ ] Auth with valid API key via X-API-Key header -> 200
- [ ] Auth with invalid API key -> 401

---

## Feature Verification

### Alert Types to Test
| Alert Type | Trigger Condition |
|-----------|-------------------|
| `price_drop` | Scan detects price decrease on monitored products |
| `price_increase` | Scan detects price increase on monitored products |
| `new_product` | Scan discovers new products on competitor store |
| `out_of_stock` | Scan detects products removed from competitor |
| `back_in_stock` | Scan detects previously removed products re-appearing |

### Plan Limits to Verify
| Resource | Free | Pro | Enterprise |
|----------|------|-----|------------|
| Competitors | 3 | 25 | Unlimited (-1) |
| Products tracked | 50 | 2,500 | Unlimited (-1) |
| Scan frequency | Weekly | Daily | Hourly |
| Price alerts | No | Yes | Yes + API |
| Source finding | No | Yes | Yes + Bulk |
| Trial days | 0 | 14 | 14 |
| API access | No | Yes | Yes |

### Dashboard Pages to Verify
| Page | Route | Key Behaviors |
|------|-------|--------------|
| Dashboard Home | `/` | KPI cards load, animated counters, quick action links work |
| Competitors | `/competitors` | Table displays, add dialog validates fields, delete confirms, pagination |
| Products | `/products` | Grid displays, filters toggle, sort works, price history dialog opens |
| Billing | `/billing` | Plan cards display correct pricing, checkout redirects |
| API Keys | `/api-keys` | Create shows raw key once, list hides raw key, revoke works |
| Settings | `/settings` | User settings display and save |
| Login | `/login` | Form validates, redirects on success |
| Register | `/register` | Form validates, redirects on success |
