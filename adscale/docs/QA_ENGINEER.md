# QA Engineer Guide

**For QA Engineers:** This guide covers testing strategy, test execution, API endpoint verification, and quality checklists for the AdScale AI Ad Campaign Manager service. AdScale manages advertising campaigns across Google Ads and Meta Ads with AI-generated ad copy, automated optimization rules, and ROAS-based performance tracking.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| pytest | Test framework and runner |
| pytest-asyncio | Async test support for FastAPI |
| httpx.AsyncClient | HTTP client for API-level testing (no server required) |
| SQLAlchemy + NullPool | Database isolation with per-test truncation |
| PostgreSQL 16 | Same database engine as production |

---

## Running Tests

### Execute All 164 Tests

```bash
# From the service root
make test-backend

# Verbose output with test names
cd backend && pytest -v

# With timing information
cd backend && pytest -v --durations=10
```

### Run Specific Test Suites

```bash
# Auth tests (11 tests)
cd backend && pytest tests/test_auth.py -v

# Ad account tests (15 tests)
cd backend && pytest tests/test_accounts.py -v

# Campaign tests (20 tests)
cd backend && pytest tests/test_campaigns.py -v

# Creative tests (16 tests)
cd backend && pytest tests/test_creatives.py -v

# Optimization rule tests (20+ tests)
cd backend && pytest tests/test_rules.py -v

# Billing tests (9 tests)
cd backend && pytest tests/test_billing.py -v

# API key tests (5 tests)
cd backend && pytest tests/test_api_keys.py -v

# Health check test (1 test)
cd backend && pytest tests/test_health.py -v
```

### Run a Single Test

```bash
cd backend && pytest tests/test_campaigns.py::test_create_campaign_success -v
```

---

## Test Coverage by Module

| Test File | Count | Covers |
|-----------|-------|--------|
| `test_auth.py` | 11 | Register (success, duplicate 409, short password 422), login (success, wrong password 401, nonexistent 401), refresh (success, wrong token type 401), profile (success, unauth 401) |
| `test_accounts.py` | 15 | Connect Google/Meta (201), duplicate (409), same ID different platform, unauthenticated (401), list empty/with data/pagination, user isolation, disconnect success (204)/not found (404)/invalid UUID (400)/other user (404) |
| `test_campaigns.py` | 20 | Create success (201)/all objectives/lifetime budget/unauthenticated (401), list empty/with data/pagination/user isolation, get by ID (200)/not found (404)/invalid UUID (400), update name/budget/status/objective/not found (404), delete success (204)/not found (404)/other user (404)/invalid UUID (400) |
| `test_creatives.py` | 16 | Create success (201)/custom CTA/invalid ad group (400)/unauthenticated (401), list empty/with data/filter by ad group/user isolation, get by ID (200)/not found (404)/invalid UUID (400), update headline/status/not found (404), delete success (204)/not found (404)/other user (404), AI copy generation (200)/minimal fields/unauthenticated (401) |
| `test_rules.py` | 20+ | Create success (201)/all types/inactive/custom conditions/unauthenticated (401), list empty/with data/pagination/user isolation, get by ID (200)/not found (404)/invalid UUID (400)/other user (404), update name/threshold/deactivate/type/conditions/not found (404), delete success (204)/not found (404)/other user (404)/invalid UUID (400), execute-now no campaigns/not found (404)/invalid UUID (400)/unauthenticated (401) |
| `test_billing.py` | 9 | List plans (200, 3 tiers), plan pricing details, checkout Pro (201), checkout Free (400), duplicate subscription (400), billing overview (200), overview after subscribe, current subscription none/after subscribe |
| `test_api_keys.py` | 5 | Create key (201, raw key returned), list keys (no raw key), revoke key (204), auth via X-API-Key (200), invalid API key (401) |
| `test_health.py` | 1 | Health check returns status, service name, timestamp |
| `test_platform_webhooks.py` | -- | Platform event webhook handling |

---

## Test Structure and Patterns

### Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Single event loop shared across all tests |
| `setup_db` | function (autouse) | Creates tables before test, truncates all tables after each test |
| `db` | function | Raw async database session for direct DB queries |
| `client` | function | `httpx.AsyncClient` configured for the FastAPI app |
| `auth_headers` | function | Pre-registered user with `{"Authorization": "Bearer <token>"}` |

### Helper Functions

| Helper | Location | Purpose |
|--------|----------|---------|
| `register_and_login(client, email)` | conftest.py | Registers a user and returns auth headers dict |
| `_connect_account(client, headers, ...)` | test_accounts.py | Connects a Google/Meta ad account |
| `_create_ad_account(client, headers, ...)` | test_campaigns.py | Creates an ad account, returns its UUID |
| `_create_campaign(client, headers, ...)` | test_campaigns.py | Creates a campaign, returns the raw response |
| `_setup_chain(client, headers, ...)` | test_creatives.py | Creates the full account -> campaign -> ad group chain |
| `_create_creative(client, headers, ...)` | test_creatives.py | Creates an ad creative in an ad group |
| `_create_rule(client, headers, ...)` | test_rules.py | Creates an optimization rule |

### Database Isolation

Each test is fully isolated:
1. Tables are created via `Base.metadata.create_all` before each test
2. After each test, all non-self PostgreSQL connections are terminated (prevents deadlocks)
3. All tables are `TRUNCATE CASCADE`-d in reverse dependency order

---

## API Documentation

Interactive Swagger UI is available at **http://localhost:8107/docs** when the backend is running.

### Endpoint Summary

#### Auth (`/api/v1/auth`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/auth/register` | None | 201 | Register new user, returns JWT tokens |
| POST | `/auth/login` | None | 200 | Login with email/password, returns JWT tokens |
| POST | `/auth/refresh` | None | 200 | Refresh tokens using refresh_token |
| GET | `/auth/me` | JWT | 200 | Get authenticated user profile |
| POST | `/auth/forgot-password` | None | 200 | Request password reset (always succeeds) |
| POST | `/auth/provision` | API Key | 201 | Provision user from platform |

#### Ad Accounts (`/api/v1/accounts`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/accounts` | JWT | 201 | Connect Google/Meta ad account |
| GET | `/accounts` | JWT | 200 | List ad accounts (paginated) |
| DELETE | `/accounts/{id}` | JWT | 204 | Disconnect ad account (soft delete) |

#### Campaigns (`/api/v1/campaigns`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/campaigns` | JWT | 201 | Create campaign (enforces plan limits) |
| GET | `/campaigns` | JWT | 200 | List campaigns (paginated) |
| GET | `/campaigns/{id}` | JWT | 200 | Get campaign by ID |
| PATCH | `/campaigns/{id}` | JWT | 200 | Update campaign (partial) |
| DELETE | `/campaigns/{id}` | JWT | 204 | Delete campaign (cascade ad groups, creatives, metrics) |

#### Ad Groups (`/api/v1/ad-groups`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/ad-groups` | JWT | 201 | Create ad group (enforces plan limits) |
| GET | `/ad-groups` | JWT | 200 | List ad groups (optional `?campaign_id=` filter) |
| GET | `/ad-groups/{id}` | JWT | 200 | Get ad group by ID |
| PATCH | `/ad-groups/{id}` | JWT | 200 | Update ad group (partial) |
| DELETE | `/ad-groups/{id}` | JWT | 204 | Delete ad group (cascade creatives) |

#### Creatives (`/api/v1/creatives`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/creatives` | JWT | 201 | Create ad creative |
| GET | `/creatives` | JWT | 200 | List creatives (optional `?ad_group_id=` filter) |
| GET | `/creatives/{id}` | JWT | 200 | Get creative by ID |
| PATCH | `/creatives/{id}` | JWT | 200 | Update creative (partial) |
| DELETE | `/creatives/{id}` | JWT | 204 | Delete creative |
| POST | `/creatives/generate-copy` | JWT | 200 | AI-generate headline, description, CTA |

#### Metrics (`/api/v1/metrics`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/metrics/overview` | JWT | 200 | Aggregated metrics (spend, revenue, ROAS, CTR, CPA) |
| GET | `/metrics/campaign/{id}` | JWT | 200 | Daily metrics for specific campaign (paginated) |
| GET | `/metrics/date-range` | JWT | 200 | Metrics within date range across all campaigns |

#### Optimization Rules (`/api/v1/rules`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/rules` | JWT | 201 | Create optimization rule |
| GET | `/rules` | JWT | 200 | List rules (paginated) |
| GET | `/rules/{id}` | JWT | 200 | Get rule by ID |
| PATCH | `/rules/{id}` | JWT | 200 | Update rule (partial) |
| DELETE | `/rules/{id}` | JWT | 204 | Delete rule |
| POST | `/rules/{id}/execute` | JWT | 200 | Execute rule immediately against active campaigns |

#### Billing (`/api/v1/billing`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/billing/plans` | None | 200 | List all plan tiers with pricing |
| POST | `/billing/checkout` | JWT | 201 | Create Stripe checkout session |
| POST | `/billing/portal` | JWT | 200 | Create Stripe customer portal session |
| GET | `/billing/current` | JWT | 200 | Get current subscription (or null) |
| GET | `/billing/overview` | JWT | 200 | Full billing overview (plan + usage) |

#### API Keys (`/api/v1/api-keys`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/api-keys` | JWT | 201 | Create API key (raw key returned once) |
| GET | `/api-keys` | JWT | 200 | List API keys (no raw keys) |
| DELETE | `/api-keys/{id}` | JWT | 204 | Revoke (deactivate) API key |

#### Usage & Health

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/usage` | JWT or API Key | 200 | Usage metrics for billing period |
| GET | `/health` | None | 200 | Service health check |

---

## Verification Checklist

### Authentication Flow

- [ ] Register new user returns `201` with `access_token` and `refresh_token`
- [ ] Duplicate email registration returns `409`
- [ ] Short password (< 8 chars) returns `422`
- [ ] Login with correct credentials returns `200` with tokens
- [ ] Login with wrong password returns `401`
- [ ] Token refresh with valid refresh_token returns new token pair
- [ ] Token refresh with access_token (wrong type) returns `401`
- [ ] `/auth/me` with valid token returns user profile with `plan: "free"`
- [ ] All protected endpoints return `401` without authentication

### Ad Account Management

- [ ] Connect Google Ads account returns `201` with `platform: "google"`, `is_connected: true`, `status: "active"`
- [ ] Connect Meta Ads account returns `201` with `platform: "meta"`
- [ ] Duplicate connection (same external ID + platform) returns `409`
- [ ] Same external ID on different platforms does NOT conflict
- [ ] List accounts with pagination (offset/limit) returns correct `total`, `items`, `offset`, `limit`
- [ ] User A cannot see User B's accounts
- [ ] Disconnect sets `is_connected: false`, `status: "paused"`
- [ ] Disconnect nonexistent account returns `404`
- [ ] Invalid UUID format returns `400`

### Campaign Management

- [ ] Create campaign with all 4 objectives: traffic, conversions, awareness, sales
- [ ] Create campaign with daily budget vs. lifetime budget
- [ ] Campaign platform is auto-set from ad account platform
- [ ] Campaign status defaults to `draft`
- [ ] List campaigns returns paginated results
- [ ] Update campaign name, budget, status, objective via `PATCH`
- [ ] Delete campaign returns `204` and cascades to ad groups
- [ ] User isolation: User B cannot see/modify/delete User A's campaigns
- [ ] Plan limit enforcement: Free user with 2 campaigns gets `403` on 3rd

### Ad Group Management

- [ ] Create ad group with targeting JSON and bid strategy
- [ ] Ad group validates campaign ownership
- [ ] List ad groups with optional `campaign_id` filter
- [ ] Plan limit enforcement: Free user with 5 ad groups gets `403` on 6th
- [ ] Delete ad group cascades to creatives

### Creative Management

- [ ] Create creative with headline, description, destination URL, CTA
- [ ] Creative validates ownership through full chain (ad_group -> campaign -> user)
- [ ] List creatives with optional `ad_group_id` filter
- [ ] AI copy generation returns non-empty `headline`, `description`, `call_to_action`
- [ ] AI copy generation with all optional fields (target_audience, tone)

### Optimization Rules

- [ ] Create rules with all 4 types: `pause_low_roas`, `scale_high_roas`, `adjust_bid`, `increase_budget`
- [ ] Rules accept arbitrary JSON conditions
- [ ] Execute-now with no active campaigns returns `campaigns_affected: 0`
- [ ] Rule execution increments `executions_count` and sets `last_executed`
- [ ] User isolation on all rule operations

### Billing

- [ ] `/billing/plans` returns 3 tiers: free, pro, enterprise (public, no auth)
- [ ] Free plan: `price_monthly_cents: 0`, `trial_days: 0`
- [ ] Checkout for Pro plan returns `checkout_url` and `session_id`
- [ ] Checkout for Free plan returns `400`
- [ ] Duplicate subscription returns `400`
- [ ] Billing overview reflects current plan and usage metrics

### API Keys

- [ ] Create key returns raw key (only time it is shown)
- [ ] List keys does NOT include raw key values
- [ ] Revoked key shows `is_active: false` in list
- [ ] `X-API-Key` header successfully authenticates to `/usage`
- [ ] Invalid API key returns `401`

---

## Feature Verification Matrix

| Feature | Free Tier | Pro Tier | Enterprise Tier |
|---------|-----------|----------|-----------------|
| Campaigns | Up to 2 | Up to 25 | Unlimited |
| Ad Groups | Up to 5 | Up to 100 | Unlimited |
| Platforms | 1 (Google OR Meta) | Google + Meta | All + API |
| AI Copy | 5/month | Unlimited | Priority AI |
| Auto-Optimization | Manual only | Yes + ROAS tracking | Yes + ROAS targets |
| API Key Access | No | Yes | Yes |
| Trial Days | None | 14 days | 14 days |

### Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

Validation errors (422) include field-level details:

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "error description",
      "type": "error_type"
    }
  ]
}
```
