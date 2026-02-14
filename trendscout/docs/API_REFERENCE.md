# TrendScout API Reference

> Part of [TrendScout](README.md) documentation

Complete API endpoint reference for the TrendScout service. For detailed request/response schemas and interactive testing, see the Swagger documentation.

---

## Base URL

All endpoints are prefixed with `/api/v1/`.

**Full API documentation** is available at:
- **Swagger UI**: http://localhost:8101/docs (interactive testing)
- **ReDoc**: http://localhost:8101/redoc (detailed schemas)
- **OpenAPI JSON**: http://localhost:8101/openapi.json

---

## Authentication

Two authentication methods are supported:

### Bearer JWT Token (Dashboard Users)

```
Authorization: Bearer <access_token>
```

Used by dashboard users after login. Access tokens expire after 15 minutes. Refresh tokens expire after 7 days.

### API Key (Programmatic Access)

```
X-API-Key: <api_key>
```

Used by programmatic integrations (Pro and Enterprise plans only). API keys are long-lived and can be revoked.

---

## Response Conventions

### Paginated Lists

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

Query parameters: `?page=1&per_page=20`

### Errors

```json
{
  "detail": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (delete) |
| 400 | Bad Request (validation) |
| 401 | Unauthorized |
| 403 | Forbidden (plan limit) |
| 404 | Not Found |
| 409 | Conflict (duplicate) |
| 422 | Schema validation error |

---

## Auth Endpoints

Base path: `/api/v1/auth/`

| Method | Path | Auth | Description | Returns |
|--------|------|------|-------------|---------|
| POST | `/register` | None | Create account | JWT tokens (201) |
| POST | `/login` | None | Login with email/password | JWT tokens (200) |
| POST | `/refresh` | None | Refresh access token | New JWT pair (200) |
| GET | `/me` | JWT | Get user profile | User object (200) |
| POST | `/provision` | JWT/API Key | Provision user from platform | User ID + API key (201) |

**Common Errors**: 401 (invalid credentials), 409 (duplicate email), 422 (validation)

---

## Research Endpoints

Base path: `/api/v1/research/`

| Method | Path | Auth | Description | Returns |
|--------|------|------|-------------|---------|
| POST | `/runs` | JWT | Create research run | Run object in pending status (201) |
| GET | `/runs` | JWT | List runs (paginated) | Paginated run list (200) |
| GET | `/runs/{run_id}` | JWT | Get run with results | Run + results array (200) |
| DELETE | `/runs/{run_id}` | JWT | Delete run (cascade) | No content (204) |
| GET | `/results/{result_id}` | JWT | Get single result detail | Result with AI analysis (200) |

**Key Features**:
- Supports custom `score_config` override
- Enforces plan limits (Free: 5/month, Pro: 50/month, Enterprise: unlimited)
- Valid sources: `aliexpress`, `tiktok`, `google_trends`, `reddit`

**Common Errors**: 403 (plan limit exceeded), 404 (not found or wrong user), 422 (empty keywords)

---

## Watchlist Endpoints

Base path: `/api/v1/watchlist/`

| Method | Path | Auth | Description | Returns |
|--------|------|------|-------------|---------|
| POST | `/` | JWT | Add result to watchlist | Item + result snapshot (201) |
| GET | `/` | JWT | List items (filter by status) | Paginated item list (200) |
| PATCH | `/{item_id}` | JWT | Update status/notes | Updated item (200) |
| DELETE | `/{item_id}` | JWT | Remove from watchlist | No content (204) |

**Key Features**:
- Status filter: `?status=watching|imported|dismissed`
- Enforces plan limits (Free: 25, Pro: 500, Enterprise: unlimited)
- Prevents duplicates (409 on re-add)
- Includes result snapshot (title, source, price, score)

**Common Errors**: 403 (limit exceeded), 404 (result not found), 409 (already in watchlist)

---

## Source Endpoints

Base path: `/api/v1/sources/`

| Method | Path | Auth | Description | Returns |
|--------|------|------|-------------|---------|
| POST | `/` | JWT | Create source config | Config with `has_credentials` flag (201) |
| GET | `/` | JWT | List source configs | Config list (200) |
| PATCH | `/{config_id}` | JWT | Update config | Updated config (200) |
| DELETE | `/{config_id}` | JWT | Delete config | No content (204) |

**Valid Source Types**: `aliexpress`, `tiktok`, `google_trends`, `reddit`

**Security**: Credentials are never returned in responses. Only `has_credentials` boolean is exposed.

**Common Errors**: 400 (invalid source_type), 404 (not found or wrong user)

---

## Billing Endpoints

Base path: `/api/v1/billing/`

| Method | Path | Auth | Description | Returns |
|--------|------|------|-------------|---------|
| GET | `/plans` | None | List all plan tiers | Plan details (200) |
| POST | `/checkout` | JWT | Create Stripe checkout | Checkout URL + session ID (201) |
| POST | `/portal` | JWT | Create customer portal | Portal URL (200) |
| GET | `/current` | JWT | Get current subscription | Subscription details (200) |
| GET | `/overview` | JWT | Billing + usage overview | Full billing state (200) |

**Plans**: Free ($0), Pro ($29), Enterprise ($99)

**Common Errors**: 400 (free plan checkout rejected, no active subscription), 401

---

## API Key Endpoints

Base path: `/api/v1/api-keys/`

| Method | Path | Auth | Description | Returns |
|--------|------|------|-------------|---------|
| POST | `/` | JWT | Create API key | Key object with raw key (201) |
| GET | `/` | JWT | List keys | Key list (no raw keys) (200) |
| DELETE | `/{key_id}` | JWT | Revoke key | No content (204) |

**Note**: Raw key is only returned once at creation time. Cannot be retrieved later.

**Common Errors**: 401, 404 (key not found)

---

## Utility Endpoints

| Method | Path | Auth | Description | Returns |
|--------|------|------|-------------|---------|
| GET | `/usage` | API Key | Usage metrics | Usage object (200) |
| GET | `/health` | None | Health check | Service metadata (200) |

---

## Request/Response Examples

For detailed request/response schemas, field descriptions, and validation rules, see:
- **Swagger UI**: http://localhost:8101/docs
- **ReDoc**: http://localhost:8101/redoc

### Sample Research Run Creation

```bash
curl -X POST http://localhost:8101/api/v1/research/runs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["wireless earbuds", "LED lights"],
    "sources": ["aliexpress", "tiktok"],
    "score_config": {
      "social": 0.5,
      "market": 0.3,
      "competition": 0.1,
      "seo": 0.05,
      "fundamentals": 0.05
    }
  }'
```

### Sample Watchlist Add

```bash
curl -X POST http://localhost:8101/api/v1/watchlist \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "result_id": "uuid",
    "notes": "Check supplier reviews"
  }'
```

### Sample API Key Auth

```bash
curl -X GET http://localhost:8101/api/v1/usage \
  -H "X-API-Key: trs_live_abc123..."
```

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md)*
