# QA Engineer Guide

**For QA Engineers:** This guide covers the full testing strategy for ContentForge, including the test stack, how to run tests, what each test file covers, API endpoint reference, and a verification checklist for manual testing.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| pytest | Test runner and framework |
| pytest-asyncio | Async test support for FastAPI |
| httpx (AsyncClient) | HTTP test client (replaces requests for async) |
| SQLAlchemy (async) | Direct DB access in test fixtures |
| PostgreSQL 16 | Test database (same as dev, tables truncated between tests) |

---

## Running Tests

### Run All Backend Tests

```bash
make test-backend
```

### Run by Test File

```bash
cd backend && pytest tests/test_auth.py -v          # Authentication
cd backend && pytest tests/test_content.py -v        # Content generation
cd backend && pytest tests/test_templates.py -v      # Template management
cd backend && pytest tests/test_images.py -v         # Image management
cd backend && pytest tests/test_billing.py -v        # Billing & subscriptions
cd backend && pytest tests/test_api_keys.py -v       # API key management
cd backend && pytest tests/test_health.py -v         # Health check
```

### Run a Single Test

```bash
cd backend && pytest tests/test_content.py::test_create_generation_job_from_url -v
```

---

## Test Coverage

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_auth.py` | 10 | Registration, login, refresh, profile, duplicate email, invalid credentials |
| `test_content.py` | 13 | Generation lifecycle, plan limits, pagination, bulk generation, user isolation, image jobs |
| `test_templates.py` | 17 | Custom template CRUD, system template protection, partial updates, user isolation, prompt override |
| `test_images.py` | 12 | Image listing, pagination, retrieval, deletion, user isolation, cross-job images, job independence |
| `test_billing.py` | 9 | Plan listing, checkout, duplicate subscription, billing overview, current subscription |
| `test_api_keys.py` | 5 | Key creation, listing, revocation, API key authentication, invalid key |
| `test_health.py` | 1 | Health endpoint returns status ok |
| `test_platform_webhooks.py` | -- | Platform event webhook handling |
| **Total** | **116** | |

---

## Test Structure

### Fixtures (conftest.py)

| Fixture | Type | Description |
|---------|------|-------------|
| `event_loop` | Session | Single event loop shared by all tests |
| `setup_db` | Autouse (function) | Creates tables before test, truncates ALL tables after each test |
| `db` | Function | Raw `AsyncSession` for direct database operations |
| `client` | Function | `httpx.AsyncClient` configured for the FastAPI app |
| `auth_headers` | Function | Pre-authenticated Bearer token headers |

### Helper Function

```python
register_and_login(client, email=None) -> dict
```

Registers a user and returns `{"Authorization": "Bearer <token>"}` headers. If no email is provided, a random one is generated. Used by virtually every test that requires authentication.

### Test Isolation

- **Database truncation**: All tables are truncated with `CASCADE` after every test via the `setup_db` fixture
- **Connection cleanup**: Other database connections are terminated before truncation to prevent deadlocks
- **Mock mode**: Stripe is in mock mode (no real payments). AI content uses mock generation (realistic text without Claude API calls).
- **Independent tests**: Each test creates its own user(s) and data from scratch

---

## API Documentation

The FastAPI auto-generated docs are available at:

- **Swagger UI**: http://localhost:8102/docs
- **ReDoc**: http://localhost:8102/redoc

---

## API Response Format

### Success Responses

**Single resource:**
```json
{
  "id": "uuid",
  "field": "value",
  "created_at": "2026-01-15T10:30:00Z"
}
```

**Paginated list:**
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### Error Responses

```json
{
  "detail": "Human-readable error message"
}
```

Common status codes: 400 (bad request), 401 (not authenticated), 403 (forbidden / plan limit exceeded), 404 (not found), 409 (conflict / duplicate), 422 (validation error).

---

## Endpoint Summary

### Auth Endpoints (`/api/v1/auth`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/auth/register` | No | 201 | Register new user, returns JWT tokens |
| POST | `/auth/login` | No | 200 | Login with email/password, returns JWT tokens |
| POST | `/auth/refresh` | No | 200 | Refresh access token using refresh token |
| GET | `/auth/me` | JWT | 200 | Get authenticated user profile |
| POST | `/auth/forgot-password` | No | 200 | Request password reset (always returns success) |
| POST | `/auth/provision` | API Key | 201 | Provision user from dropshipping platform |

### Content Generation Endpoints (`/api/v1/content`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/content/generate` | JWT | 201 | Create single generation job (enforces plan limits) |
| POST | `/content/generate/bulk` | JWT | 201 | Bulk generate from URLs or CSV data |
| GET | `/content/jobs` | JWT | 200 | List generation jobs (paginated) |
| GET | `/content/jobs/{job_id}` | JWT | 200 | Get job with all content items and images |
| DELETE | `/content/jobs/{job_id}` | JWT | 204 | Delete job and all associated content/images |
| PATCH | `/content/{content_id}` | JWT | 200 | Edit generated content text |

### Template Endpoints (`/api/v1/templates`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/templates/` | JWT | 201 | Create custom template |
| GET | `/templates/` | JWT | 200 | List system + user templates |
| GET | `/templates/{template_id}` | JWT | 200 | Get template by ID |
| PATCH | `/templates/{template_id}` | JWT | 200 | Update custom template (partial) |
| DELETE | `/templates/{template_id}` | JWT | 204 | Delete custom template |

### Image Endpoints (`/api/v1/images`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/images/` | JWT | 200 | List processed images (paginated) |
| GET | `/images/{image_id}` | JWT | 200 | Get single image details |
| DELETE | `/images/{image_id}` | JWT | 204 | Delete image record |

### Billing Endpoints (`/api/v1/billing`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/billing/plans` | No | 200 | List all plan tiers with pricing |
| POST | `/billing/checkout` | JWT | 201 | Create Stripe checkout session |
| POST | `/billing/portal` | JWT | 200 | Create Stripe customer portal session |
| GET | `/billing/current` | JWT | 200 | Get current subscription (or null) |
| GET | `/billing/overview` | JWT | 200 | Full billing overview with usage metrics |

### API Key Endpoints (`/api/v1/api-keys`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/api-keys` | JWT | 201 | Create API key (returns raw key once) |
| GET | `/api-keys` | JWT | 200 | List API keys (no raw keys) |
| DELETE | `/api-keys/{key_id}` | JWT | 204 | Revoke (deactivate) API key |

### Other Endpoints

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/health` | No | 200 | Service health check |
| GET | `/usage` | JWT or API Key | 200 | Current usage metrics for billing period |
| POST | `/webhooks/stripe` | Stripe Signature | 200 | Handle Stripe webhook events |

---

## Verification Checklist

### Authentication Flow

- [ ] Register with valid email/password -- returns 201 with access and refresh tokens
- [ ] Register with duplicate email -- returns 409
- [ ] Register with short password (< 8 chars) -- returns 422
- [ ] Login with correct credentials -- returns 200 with tokens
- [ ] Login with wrong password -- returns 401
- [ ] Login with nonexistent email -- returns 401
- [ ] Refresh with valid refresh token -- returns 200 with new tokens
- [ ] Refresh with access token (not refresh) -- returns 401
- [ ] GET /auth/me with valid token -- returns 200 with user profile
- [ ] GET /auth/me without token -- returns 401

### Content Generation Flow

- [ ] Create generation from URL -- job completed with 5 content types
- [ ] Create generation from manual data -- job completed with requested content types
- [ ] Free tier: 11th generation -- returns 403 with "limit" in message
- [ ] List jobs with pagination -- correct total, page, per_page
- [ ] Get job by ID -- includes content_items and image_items
- [ ] Delete job -- returns 204, subsequent GET returns 404
- [ ] Edit content text -- returns updated content with recalculated word_count
- [ ] Bulk generation from URLs -- creates multiple completed jobs
- [ ] Generation with image_urls -- creates image_items with completed status
- [ ] User A cannot access User B's jobs -- returns 404

### Template Management

- [ ] Create custom template -- returns 201 with all fields
- [ ] Create with minimal fields -- defaults applied (professional tone, detailed style)
- [ ] List templates -- includes both system and custom templates
- [ ] Get template by ID -- returns correct template
- [ ] Partial update (PATCH) -- only updates provided fields
- [ ] Full update (PATCH) -- all fields updated including prompt_override
- [ ] Delete custom template -- returns 204, subsequent GET returns 404
- [ ] System template visible to all users
- [ ] System template PATCH -- returns 403
- [ ] System template DELETE -- returns 403
- [ ] User A cannot access User B's custom templates

### Image Management

- [ ] List images -- paginated, includes format/width/height/size_bytes
- [ ] List images pagination -- correct page sizes
- [ ] Empty image list -- returns `{ items: [], total: 0 }`
- [ ] Get image by ID -- correct fields
- [ ] Delete image -- returns 204, does NOT delete parent job
- [ ] User A cannot access User B's images
- [ ] Images from multiple jobs appear in same list

### Billing

- [ ] GET /billing/plans -- returns 3 plans (free, pro, enterprise) with pricing
- [ ] Checkout pro plan -- returns 201 with checkout_url and session_id
- [ ] Checkout free plan -- returns 400
- [ ] Duplicate subscription -- returns 400
- [ ] Billing overview -- includes current_plan, plan_name, usage metrics
- [ ] Current subscription (no subscription) -- returns null
- [ ] Current subscription (after checkout) -- returns active subscription

### API Keys

- [ ] Create key -- returns 201 with raw key (shown once)
- [ ] List keys -- returns keys without raw key values
- [ ] Revoke key -- returns 204, key marked as inactive
- [ ] Auth via X-API-Key header -- returns 200 on /usage endpoint
- [ ] Auth via invalid API key -- returns 401

---

## Feature Verification

| Feature | Expected Behavior | Endpoint(s) |
|---------|------------------|-------------|
| Plan limit enforcement | Free: 10 gens/month, Pro: 200, Enterprise: unlimited | POST `/content/generate` |
| Image limit enforcement | Free: 5/month, Pro: 100, Enterprise: unlimited | POST `/content/generate` with `image_urls` |
| Content types | title, description, meta_description, keywords, bullet_points | POST `/content/generate` |
| Source types | "url", "manual", "csv" | POST `/content/generate` |
| Job status transitions | pending -> processing -> completed OR failed | GET `/content/jobs/{id}` |
| System template protection | Cannot PATCH or DELETE system templates (403) | PATCH/DELETE `/templates/{id}` |
| User isolation | Users cannot read, update, or delete other users' resources | All authenticated endpoints |
| API key hashing | Keys are SHA-256 hashed; raw key only returned at creation | POST `/api-keys` |
| Mock Stripe mode | Checkout creates subscription directly in DB without Stripe | POST `/billing/checkout` |
| Webhook handling | Processes `customer.subscription.created/updated/deleted` | POST `/webhooks/stripe` |
| Psychological pricing | round_99 ($X.99), round_95 ($X.95), round_00 ($X.00), none | Pricing service (unit tested) |
