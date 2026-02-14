# AdScale API Reference

> Part of [AdScale](README.md) documentation

Complete endpoint reference for the AdScale ad campaign management API.

---

## Conventions

| Item | Detail |
|------|--------|
| **Base URL** | `http://localhost:8107/api/v1` |
| **Interactive docs** | `http://localhost:8107/docs` (Swagger UI) |
| **IDs** | UUID v4 strings |
| **Timestamps** | ISO 8601 UTC (`2026-02-14T12:34:56Z`) |
| **Pagination** | `?offset=0&limit=50` on list endpoints; response includes `items`, `total`, `offset`, `limit` |

### Authentication

| Method | Header | Use Case |
|--------|--------|----------|
| JWT Bearer | `Authorization: Bearer <token>` | Dashboard / user requests |
| API Key | `X-API-Key: <raw_key>` | Programmatic / server-to-server |

**Public endpoints (no auth):** `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/forgot-password`, `/billing/plans`, `/health`

**Dual-auth endpoints (JWT or API Key):** `/auth/provision`, `/usage`

### Error Format

All errors return `{"detail": "message"}`. Validation errors (422) return an array of field-level details with `loc`, `msg`, and `type`.

---

## Auth (`/auth`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/auth/register` | None | 201 | Create account; returns access + refresh tokens |
| POST | `/auth/login` | None | 200 | Authenticate; returns access + refresh tokens |
| POST | `/auth/refresh` | None | 200 | Exchange refresh token for new token pair |
| GET | `/auth/me` | JWT | 200 | Current user profile (id, email, plan) |
| POST | `/auth/provision` | JWT or API Key | 201 | Platform-initiated user provisioning |

### Auth Notes

- **Register/Login response:** `access_token`, `refresh_token`, `token_type` ("bearer").
- **Register request:** `email` (unique), `password` (min 8 chars).
- **Refresh request:** `refresh_token` string.
- **Provision request:** `email`, `external_user_id`. Returns `user_id`, `email`, `plan`.
- **Key errors:** 409 duplicate email on register, 401 invalid credentials on login, 422 password < 8 chars.

---

## Ad Accounts (`/accounts`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/accounts` | JWT | 201 | Connect an ad account (Google, Meta, etc.) |
| GET | `/accounts` | JWT | 200 | List connected accounts (paginated) |
| DELETE | `/accounts/{id}` | JWT | 204 | Disconnect an ad account |

### Account Fields

- `platform` -- `google` or `meta` (required on create)
- `account_id_external` -- External platform account ID (required on create)
- `account_name` -- Display name for the account
- `access_token` -- Optional OAuth token for platform API access
- `is_connected` -- Boolean, reflects connection status
- `status` -- `active` or `disconnected`
- `connected_at` -- Timestamp of initial connection

**Key errors:** 409 duplicate (same external ID + platform + user), 404 not found on disconnect, 400 invalid UUID.

---

## Campaigns (`/campaigns`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/campaigns` | JWT | 201 | Create campaign (linked to ad account) |
| GET | `/campaigns` | JWT | 200 | List campaigns (paginated) |
| GET | `/campaigns/{id}` | JWT | 200 | Get campaign details |
| PATCH | `/campaigns/{id}` | JWT | 200 | Update campaign (partial) |
| DELETE | `/campaigns/{id}` | JWT | 204 | Delete campaign (cascades to ad groups, creatives, metrics) |

### Campaign Fields

- `ad_account_id` -- UUID of the linked ad account (required on create)
- `name` -- Campaign name
- `platform` -- Denormalized from ad account (read-only)
- `objective` -- One of: `sales`, `traffic`, `awareness`, `leads`, `app_installs`
- `budget_daily` -- Daily budget in USD (mutually exclusive with `budget_lifetime`)
- `budget_lifetime` -- Lifetime budget in USD
- `status` -- One of: `draft`, `active`, `paused`, `completed`
- `start_date`, `end_date` -- ISO date strings

**Plan limits:** Free: 2 campaigns, Pro: 25, Enterprise: unlimited. Returns 403 when exceeded.

**Cascade delete:** Deleting a campaign removes all child ad groups, creatives, and metrics.

---

## Ad Groups (`/ad-groups`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/ad-groups` | JWT | 201 | Create ad group within a campaign |
| GET | `/ad-groups` | JWT | 200 | List ad groups (filter by `campaign_id`, paginated) |

### Ad Group Fields

- `campaign_id` -- UUID of the parent campaign (required on create)
- `name` -- Ad group name
- `targeting` -- JSON object with targeting criteria:
  - `age` -- Age range string (e.g. "25-45")
  - `interests` -- Array of interest keywords
  - `locations` -- Array of country codes
- `bid_strategy` -- One of: `auto_cpc`, `manual_cpc`, `target_roas`
- `bid_amount` -- Manual bid amount (optional, used with `manual_cpc`)
- `status` -- One of: `active`, `paused`

**Plan limits:** Free: 5 ad groups, Pro: 100, Enterprise: unlimited.

---

## Creatives (`/creatives`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/creatives` | JWT | 201 | Create ad creative in an ad group |
| GET | `/creatives` | JWT | 200 | List creatives (filter by `ad_group_id`, paginated) |
| GET | `/creatives/{id}` | JWT | 200 | Get creative details |
| PATCH | `/creatives/{id}` | JWT | 200 | Update creative (partial) |
| DELETE | `/creatives/{id}` | JWT | 204 | Delete creative |
| POST | `/creatives/generate-copy` | JWT | 200 | AI-generate ad copy from product info |

### Creative Fields

- `ad_group_id` -- UUID of the parent ad group (required on create)
- `headline` -- Ad headline text
- `description` -- Ad body text
- `destination_url` -- Click-through URL
- `call_to_action` -- CTA text (e.g. "Shop Now", "Learn More")
- `status` -- One of: `active`, `paused`

### AI Copy Generation

`POST /creatives/generate-copy` accepts:
- `product_name` -- Name of the product to advertise
- `product_description` -- Description for context
- `target_audience` -- Who the ad should target (optional)
- `tone` -- Tone of voice: `professional`, `casual`, `energetic`, etc. (optional)

Returns: `headline`, `description`, `call_to_action`.

---

## Metrics (`/metrics`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/metrics/overview` | JWT | 200 | Aggregate metrics across all campaigns |
| GET | `/metrics/campaign/{id}` | JWT | 200 | Daily metrics for a specific campaign (paginated) |

### Overview Response

Returns aggregate totals: `total_spend`, `total_revenue`, `total_impressions`, `total_clicks`, `total_conversions`, `avg_roas`, `avg_ctr`, `avg_cpa`.

Query params: `start_date`, `end_date` (ISO date strings).

### Per-Campaign Response

Returns daily metric rows: `date`, `impressions`, `clicks`, `conversions`, `spend`, `revenue`, `roas`, `ctr`, `cpa`.

Query params: `offset`, `limit` (default pagination).

---

## Optimization Rules (`/rules`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/rules` | JWT | 201 | Create automation rule |
| GET | `/rules` | JWT | 200 | List rules (paginated) |
| GET | `/rules/{id}` | JWT | 200 | Get rule details |
| PATCH | `/rules/{id}` | JWT | 200 | Update rule (partial) |
| DELETE | `/rules/{id}` | JWT | 204 | Delete rule |
| POST | `/rules/{id}/execute` | JWT | 200 | Execute rule immediately |

### Rule Fields

- `name` -- Human-readable rule name
- `rule_type` -- One of: `pause_low_roas`, `increase_budget_high_roas`, `decrease_budget_low_ctr`, `pause_no_conversions`
- `threshold` -- Numeric threshold that triggers the rule
- `conditions` -- Additional JSON conditions (optional)
- `is_active` -- Boolean, whether the rule auto-executes
- `last_executed` -- Timestamp of most recent execution (read-only)
- `executions_count` -- Total times executed (read-only)

### Execute Response

`POST /rules/{id}/execute` returns:
- `rule_id` -- UUID of the executed rule
- `campaigns_affected` -- Count of campaigns modified
- `actions_taken` -- Array of human-readable descriptions of changes made

---

## Billing (`/billing`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/billing/plans` | None | 200 | List all plan tiers with pricing |
| POST | `/billing/checkout` | JWT | 201 | Create Stripe checkout session |
| GET | `/billing/overview` | JWT | 200 | Billing overview with usage stats |
| GET | `/billing/current` | JWT | 200 | Current subscription (or null) |

### Plan Tiers

| Plan | Price | Campaigns | Ad Groups | API Access |
|------|-------|-----------|-----------|------------|
| Free | $0/mo | 2 | 5 | No |
| Pro | $49/mo | 25 | 100 | Yes |
| Enterprise | $149/mo | Unlimited | Unlimited | Yes |

**Checkout errors:** 400 when attempting free tier or duplicate subscription.

---

## API Keys (`/api-keys`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/api-keys` | JWT | 201 | Create API key (raw key returned once) |
| GET | `/api-keys` | JWT | 200 | List keys (no raw keys shown) |
| DELETE | `/api-keys/{id}` | JWT | 204 | Revoke API key |

Key prefix: `adscale_live_`. Store the raw key securely on creation -- it is never returned again.

---

## Health

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/health` | None | 200 | Returns `status`, `service`, `timestamp` |

---

## Status Code Summary

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 204 | No Content (DELETE) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden (plan limit) |
| 404 | Not Found |
| 409 | Conflict (duplicate) |
| 422 | Validation Error |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md)*
