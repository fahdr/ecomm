# API Reference

> Part of [SpyDrop](README.md) documentation

This guide documents all SpyDrop API endpoints, request/response formats, and API conventions.

---

## API Conventions

- **Base path:** `/api/v1/`
- **Authentication:** `Authorization: Bearer <JWT>` or `X-API-Key: <key>` header
- **Pagination:** `?page=1&per_page=20` (1-based, max 100 per page)
- **Response format:** Paginated lists use `{ items: [...], total: N, page: N, per_page: N }`
- **Error format:** `{ "detail": "error message" }`
- **IDs:** UUID v4 strings
- **Timestamps:** ISO 8601 format

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET/PATCH request |
| 201 | Created | Successful POST request |
| 204 | No Content | Successful DELETE (no response body) |
| 400 | Bad Request | Invalid input (e.g., malformed UUID) |
| 401 | Unauthorized | Missing/invalid auth token or API key |
| 403 | Forbidden | Plan limit exceeded |
| 404 | Not Found | Resource does not exist (also used for authorization failures to prevent enumeration) |
| 409 | Conflict | Duplicate email during registration |
| 422 | Validation Error | Pydantic schema validation failed |

---

## Response Formats

### Paginated List

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### Single Resource

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "field": "value",
  "created_at": "2026-02-12T10:00:00Z",
  "updated_at": "2026-02-12T10:00:00Z"
}
```

### Error Response

```json
{
  "detail": "Human-readable error message"
}
```

### Token Response (Auth)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## Endpoint Summary

### Auth (`/api/v1/auth/`)

| Method | Path | Auth | Status Codes | Description |
|--------|------|------|-------------|-------------|
| POST | `/register` | None | 201, 409, 422 | Register new user; returns tokens; 409 if email exists; 422 if password < 8 chars |
| POST | `/login` | None | 200, 401 | Login with email/password; returns tokens; 401 if bad credentials |
| POST | `/refresh` | None | 200, 401 | Refresh access token; accepts refresh_token in body; 401 if invalid/expired |
| GET | `/me` | Bearer | 200, 401 | Get current user profile (email, plan, is_active) |
| POST | `/forgot-password` | None | 200 | Request password reset; always returns success (prevents email enumeration) |
| POST | `/provision` | Bearer/API Key | 201 | Create user + API key for platform integration; returns user and raw API key |

#### POST /register

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response (201):**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

#### POST /login

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response (200):**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

#### GET /me

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "plan": "free",
  "is_active": true,
  "created_at": "2026-02-12T10:00:00Z"
}
```

---

### Competitors (`/api/v1/competitors/`)

| Method | Path | Auth | Status Codes | Description |
|--------|------|------|-------------|-------------|
| POST | `/` | Bearer | 201, 403, 422 | Create competitor; 403 if plan limit reached |
| GET | `/` | Bearer | 200 | List competitors (paginated: `?page=1&per_page=20`) |
| GET | `/{id}` | Bearer | 200, 400, 404 | Get single competitor; 400 if invalid UUID; 404 if not found or wrong user |
| PATCH | `/{id}` | Bearer | 200, 400, 404 | Partial update (name, url, platform, status) |
| DELETE | `/{id}` | Bearer | 204, 400, 404 | Delete competitor (cascades to products, scans, alerts, sources) |
| GET | `/{id}/products` | Bearer | 200, 400 | List products for specific competitor (paginated) |

#### POST /competitors/

**Request:**
```json
{
  "name": "Rival Gadgets",
  "url": "https://rival-gadgets.com",
  "platform": "shopify"
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "...",
  "name": "Rival Gadgets",
  "url": "https://rival-gadgets.com",
  "platform": "shopify",
  "status": "active",
  "product_count": 0,
  "last_scanned": null,
  "created_at": "2026-02-12T10:00:00Z",
  "updated_at": "2026-02-12T10:00:00Z"
}
```

#### PATCH /competitors/{id}

**Request (partial update):**
```json
{
  "status": "paused"
}
```

**Response (200):** Returns updated competitor object.

---

### Products (`/api/v1/products/`)

| Method | Path | Auth | Status Codes | Description |
|--------|------|------|-------------|-------------|
| GET | `/` | Bearer | 200, 401, 422 | Cross-competitor product list with filters: `?status=active&sort_by=price` |
| GET | `/{id}` | Bearer | 200, 400, 404 | Product detail with full `price_history` array |

#### GET /products/

**Query Parameters:**
- `page` (int, default 1) — Page number
- `per_page` (int, default 20, max 100) — Items per page
- `status` (string, optional) — Filter by status: `active`, `removed`
- `sort_by` (string, optional) — Sort order: `last_seen`, `first_seen`, `price`, `title`

**Response (200):**
```json
{
  "items": [
    {
      "id": "...",
      "competitor_id": "...",
      "competitor_name": "Rival Gadgets",
      "title": "Wireless Earbuds",
      "url": "https://rival-gadgets.com/products/wireless-earbuds",
      "image_url": "https://...",
      "price": 49.99,
      "currency": "USD",
      "status": "active",
      "first_seen": "2026-02-10T10:00:00Z",
      "last_seen": "2026-02-12T10:00:00Z",
      "price_history": [
        {"date": "2026-02-10T10:00:00Z", "price": 59.99},
        {"date": "2026-02-12T10:00:00Z", "price": 49.99}
      ],
      "created_at": "2026-02-10T10:00:00Z",
      "updated_at": "2026-02-12T10:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

---

### Alerts (planned: `/api/v1/alerts/`)

| Method | Path | Auth | Status Codes | Description |
|--------|------|------|-------------|-------------|
| POST | `/` | Bearer | 201 | Create alert (alert_type, threshold, competitor_id or product_id) |
| GET | `/` | Bearer | 200 | Paginated list with `?is_active=true` filter |
| GET | `/{id}` | Bearer | 200, 404 | Single alert details |
| PATCH | `/{id}` | Bearer | 200, 404 | Update alert_type, threshold, is_active |
| DELETE | `/{id}` | Bearer | 204, 404 | Delete alert + history |

**Alert Types:**
- `price_drop` — Product price decreased
- `price_increase` — Product price increased
- `new_product` — New product discovered on competitor store
- `out_of_stock` — Product removed from competitor store
- `back_in_stock` — Previously removed product re-appeared

---

### Billing (`/api/v1/billing/`)

| Method | Path | Auth | Status Codes | Description |
|--------|------|------|-------------|-------------|
| GET | `/plans` | None | 200 | Public endpoint; returns 3 tiers (free, pro, enterprise) |
| POST | `/checkout` | Bearer | 201, 400 | Create checkout session; 400 if free plan or already subscribed |
| POST | `/portal` | Bearer | 200, 400 | Create Stripe customer portal URL |
| GET | `/current` | Bearer | 200 | Returns current subscription or null |
| GET | `/overview` | Bearer | 200 | Full billing overview with plan, subscription, and usage |

#### GET /plans

**Response (200):**
```json
[
  {
    "tier": "free",
    "name": "Free",
    "price_monthly": 0,
    "max_competitors": 3,
    "max_products": 50,
    "scan_frequency": "weekly",
    "features": ["Basic tracking", "No alerts", "No source finding"]
  },
  {
    "tier": "pro",
    "name": "Pro",
    "price_monthly": 29,
    "max_competitors": 25,
    "max_products": 2500,
    "scan_frequency": "daily",
    "features": ["Price alerts", "Source finding", "API access"],
    "trial_days": 14
  },
  {
    "tier": "enterprise",
    "name": "Enterprise",
    "price_monthly": 99,
    "max_competitors": -1,
    "max_products": -1,
    "scan_frequency": "hourly",
    "features": ["All alerts + API", "Bulk source finding", "Priority support"],
    "trial_days": 14
  }
]
```

---

### API Keys (`/api/v1/api-keys`)

| Method | Path | Auth | Status Codes | Description |
|--------|------|------|-------------|-------------|
| POST | `` | Bearer | 201 | Create API key; raw key returned ONLY in response |
| GET | `` | Bearer | 200 | List keys (no raw key, only key_prefix) |
| DELETE | `/{id}` | Bearer | 204, 404 | Revoke key (marks inactive, not deleted) |

#### POST /api-keys

**Response (201):**
```json
{
  "id": "...",
  "key": "spydrop_1234567890abcdef",
  "key_prefix": "spydrop_12345...",
  "is_active": true,
  "created_at": "2026-02-12T10:00:00Z"
}
```

**Note:** The `key` field is ONLY present in the creation response. Store it securely -- it cannot be retrieved later.

---

### Other Endpoints

| Method | Path | Auth | Status Codes | Description |
|--------|------|------|-------------|-------------|
| GET | `/api/v1/health` | None | 200 | Health check; returns `{ service, status, timestamp }` |
| GET | `/api/v1/usage` | Bearer/API Key | 200 | Usage metrics for cross-service integration |
| POST | `/api/v1/webhooks/stripe` | Stripe sig | 200, 400 | Stripe webhook handler for subscription lifecycle events |

#### GET /health

**Response (200):**
```json
{
  "service": "spydrop",
  "status": "ok",
  "timestamp": "2026-02-12T10:00:00Z"
}
```

#### GET /usage

**Response (200):**
```json
{
  "competitors_used": 2,
  "competitors_limit": 3,
  "products_tracked": 35,
  "products_limit": 50
}
```

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md) · [README](README.md)*
