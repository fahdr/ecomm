# RankPilot QA Engineer Guide

## Overview

RankPilot is an Automated SEO Engine with 74 backend unit tests across 8 test files. This guide covers the test infrastructure, how to run tests, what each test file verifies, and a checklist for manual feature verification.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| **pytest** | Test runner and framework |
| **pytest-asyncio** | Async test support for FastAPI + SQLAlchemy |
| **httpx.AsyncClient** | HTTP client for API integration tests |
| **SQLAlchemy 2.0 (async)** | Database ORM with NullPool for test isolation |
| **PostgreSQL 16** | Test database (same instance, tables truncated between tests) |

---

## Running Tests

```bash
# Run all 74 backend tests
make test-backend

# Verbose output (shows each test name and result)
pytest backend/tests -v

# Run a single test file
pytest backend/tests/test_sites.py -v

# Run a specific test by name
pytest backend/tests/test_blog.py::test_create_blog_post_basic -v

# Run tests matching a keyword pattern
pytest backend/tests -k "keyword" -v

# Run with print output visible
pytest backend/tests -v -s
```

---

## Test Coverage by File

| Test File | Tests | Domain |
|-----------|-------|--------|
| `test_health.py` | 1 | Health check endpoint |
| `test_auth.py` | 11 | Registration, login, refresh tokens, profile, duplicates |
| `test_sites.py` | 20 | Site CRUD, pagination, domain verification, cross-user isolation |
| `test_blog.py` | 25 | Blog post CRUD, AI generation, content/keywords, status transitions |
| `test_keywords.py` | 16 | Keyword add/list/delete, duplicates, rank refresh, pagination |
| `test_audits.py` | 15 | Audit execution, score validation, history, pagination |
| `test_billing.py` | 10 | Plan listing, checkout, overview, subscription lifecycle |
| `test_api_keys.py` | 5 | Key creation, listing, revocation, API key authentication |
| **Total** | **74** | |

---

## Test Structure and Fixtures

### conftest.py

The test configuration file (`backend/tests/conftest.py`) provides the core test infrastructure:

**`setup_db` (autouse)**
- Runs before every test automatically.
- Creates all tables via `Base.metadata.create_all`.
- After each test, terminates all non-self database connections (prevents deadlocks), then truncates all tables with `CASCADE`.

**`client`**
- Provides an `httpx.AsyncClient` configured against the FastAPI app.
- Base URL: `http://test`.

**`db`**
- Provides a raw `AsyncSession` for direct database operations in tests.

**`auth_headers`**
- Registers a new test user via `POST /api/v1/auth/register` with a random email.
- Returns `{"Authorization": "Bearer <access_token>"}`.

**`register_and_login(client, email=None)`**
- Exported helper function for creating additional users within tests.
- Used to test cross-user isolation (e.g., User A cannot access User B's resources).

### Dependency Override

The test suite overrides the `get_db` dependency to use a test session factory with `NullPool`:

```python
app.dependency_overrides[get_db] = override_get_db
```

This ensures each test gets an isolated database session that commits on success and rolls back on failure.

---

## API Documentation

Interactive API docs are available at:

- **Swagger UI**: http://localhost:8103/docs
- **ReDoc**: http://localhost:8103/redoc

All endpoints are prefixed with `/api/v1/`.

---

## Endpoint Summary

### Health (`health.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Returns service name, status "ok", and timestamp |

### Authentication (`auth.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register new user, returns JWT tokens |
| POST | `/auth/login` | No | Login with email/password, returns JWT tokens |
| POST | `/auth/refresh` | No | Refresh access token using refresh token |
| GET | `/auth/me` | JWT | Get authenticated user profile |
| POST | `/auth/forgot-password` | No | Request password reset (stub) |
| POST | `/auth/provision` | JWT/API Key | Provision user from platform (cross-service) |

### Sites (`sites.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/sites` | JWT | Create site (domain for SEO tracking) |
| GET | `/sites` | JWT | List sites with pagination |
| GET | `/sites/{site_id}` | JWT | Get site by ID |
| PATCH | `/sites/{site_id}` | JWT | Update site fields |
| DELETE | `/sites/{site_id}` | JWT | Delete site + all related data |
| POST | `/sites/{site_id}/verify` | JWT | Verify domain ownership (mock) |

### Blog Posts (`blog_posts.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/blog-posts` | JWT | Create blog post (enforces plan limit) |
| GET | `/blog-posts` | JWT | List posts with optional site_id filter |
| GET | `/blog-posts/{post_id}` | JWT | Get post by ID |
| PATCH | `/blog-posts/{post_id}` | JWT | Update post fields |
| DELETE | `/blog-posts/{post_id}` | JWT | Delete post |
| POST | `/blog-posts/generate` | JWT | Generate AI content for existing post |

### Keywords (`keywords.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/keywords` | JWT | Add keyword to track (enforces plan limit) |
| GET | `/keywords` | JWT | List keywords by site_id (required query param) |
| DELETE | `/keywords/{keyword_id}` | JWT | Remove keyword (requires site_id query param) |
| POST | `/keywords/refresh` | JWT | Refresh rank data for site keywords (mock) |

### Audits (`audits.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/audits/run` | JWT | Run SEO audit on a site (mock) |
| GET | `/audits` | JWT | List audit history by site_id |
| GET | `/audits/{audit_id}` | JWT | Get single audit result |

### Schema Markup (`schema.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/schema` | JWT | Create JSON-LD schema config |
| GET | `/schema` | JWT | List schema configs by site_id |
| GET | `/schema/{config_id}` | JWT | Get schema config by ID |
| PATCH | `/schema/{config_id}` | JWT | Update schema config |
| DELETE | `/schema/{config_id}` | JWT | Delete schema config |
| GET | `/schema/{config_id}/preview` | JWT | Preview rendered JSON-LD script tag |

### Billing (`billing.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/billing/plans` | No | List all plan tiers with pricing |
| POST | `/billing/checkout` | JWT | Create Stripe checkout session |
| POST | `/billing/portal` | JWT | Create Stripe customer portal session |
| GET | `/billing/current` | JWT | Get current subscription (or null) |
| GET | `/billing/overview` | JWT | Full billing dashboard data |

### API Keys (`api_keys.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api-keys` | JWT | Create API key (returns raw key once) |
| GET | `/api-keys` | JWT | List API keys (no raw keys) |
| DELETE | `/api-keys/{key_id}` | JWT | Revoke (deactivate) API key |

### Usage (`usage.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/usage` | JWT/API Key | Get current billing period usage metrics |

### Webhooks (`webhooks.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/webhooks/stripe` | Stripe signature | Handle subscription lifecycle events |

---

## Verification Checklist

### Authentication Flow

- [ ] Register new user returns 201 with `access_token` and `refresh_token`
- [ ] Register with duplicate email returns 409
- [ ] Register with short password (< 8 chars) returns 422
- [ ] Login with valid credentials returns 200 with tokens
- [ ] Login with wrong password returns 401
- [ ] Login with non-existent email returns 401
- [ ] Refresh with valid refresh token returns new token pair
- [ ] Refresh with access token (wrong type) returns 401
- [ ] GET /auth/me returns user profile with email, plan, is_active
- [ ] GET /auth/me without token returns 401

### Site Management

- [ ] Create site returns 201 with `domain`, `is_verified=false`, `status="pending"`
- [ ] Create site with sitemap_url stores the URL
- [ ] Create duplicate domain for same user returns 400
- [ ] Create site with domain < 3 chars returns 422
- [ ] Create site without auth returns 401
- [ ] List sites returns paginated response scoped to authenticated user
- [ ] List sites with pagination respects `page` and `per_page` params
- [ ] Get site by ID returns 200
- [ ] Get non-existent site returns 404
- [ ] Get another user's site returns 404
- [ ] Update site domain, sitemap_url, and status via PATCH
- [ ] Delete site returns 204, subsequent GET returns 404
- [ ] Delete another user's site returns 404
- [ ] Verify site sets `is_verified=true` and `status="active"`
- [ ] Verify non-existent site returns 404
- [ ] Verify another user's site returns 404

### Blog Posts

- [ ] Create post returns 201 with title, slug, status="draft", word_count
- [ ] Create post with content calculates word_count > 0
- [ ] Create post with keywords stores the keyword list
- [ ] Create post with meta_description stores it
- [ ] Create post for non-existent site returns 404
- [ ] Create post without auth returns 401
- [ ] Create post with empty title returns 422
- [ ] List posts returns paginated response
- [ ] List posts with site_id filter returns only matching posts
- [ ] Get post by ID returns correct post
- [ ] Get non-existent post returns 404
- [ ] Get another user's post returns 404
- [ ] Update post title, content, keywords, status via PATCH
- [ ] Updating content recalculates word_count
- [ ] Setting status to "published" populates published_at timestamp
- [ ] Delete post returns 204
- [ ] AI generate fills in content and meta_description
- [ ] AI generate for non-existent post returns 404
- [ ] AI generate for another user's post returns 404

### Keyword Tracking

- [ ] Add keyword returns 201 with keyword, site_id, tracked_since
- [ ] Add duplicate keyword for same site returns 400
- [ ] Add keyword for non-existent site returns 404
- [ ] Add keyword without auth returns 401
- [ ] Add keyword for another user's site returns 404
- [ ] List keywords by site_id returns paginated response
- [ ] List keywords with pagination works correctly
- [ ] List keywords for non-existent site returns 404
- [ ] Delete keyword returns 204, removed from list
- [ ] Delete non-existent keyword returns 404
- [ ] Delete keyword with wrong site_id returns 404
- [ ] Refresh ranks returns updated count and message
- [ ] Refresh ranks for non-existent site returns 404

### SEO Audits

- [ ] Run audit returns 201 with overall_score (0-100), issues list, recommendations list
- [ ] Audit issues have severity, category, and message fields
- [ ] Run audit for non-existent site returns 404
- [ ] Run audit without auth returns 401
- [ ] Run audit for another user's site returns 404
- [ ] Running multiple audits creates separate records
- [ ] List audits by site_id returns paginated response
- [ ] List audits with pagination works correctly
- [ ] List audits for non-existent site returns 404
- [ ] Get audit by ID returns correct audit with matching score
- [ ] Get non-existent audit returns 404
- [ ] Get another user's audit returns 404

### Schema Markup

- [ ] Create schema config returns 201 with page_type and schema_json
- [ ] Creating without custom schema_json generates default template
- [ ] Supported page types: product, article, faq, breadcrumb, organization
- [ ] Get schema config by ID returns correct config
- [ ] List schema configs by site_id returns paginated response
- [ ] Update schema_json and is_active via PATCH
- [ ] Delete schema config returns 204
- [ ] Preview returns rendered `<script type="application/ld+json">` tag
- [ ] Cross-user access to schema configs returns 404

### Billing

- [ ] List plans returns 3 tiers (free, pro, enterprise) -- no auth required
- [ ] Free plan has price_monthly_cents=0 and trial_days=0
- [ ] Checkout for pro plan returns 201 with checkout_url and session_id
- [ ] Checkout for free plan returns 400
- [ ] Duplicate checkout (already subscribed) returns 400
- [ ] Billing overview returns current_plan, plan_name, usage metrics
- [ ] Billing overview reflects plan upgrade after checkout
- [ ] Get current subscription returns null when unsubscribed
- [ ] Get current subscription returns subscription data after checkout

### API Keys

- [ ] Create API key returns 201 with raw key (shown once)
- [ ] Raw key is 20+ characters long
- [ ] List API keys returns key metadata without raw key values
- [ ] Revoke key sets is_active=false (returns 204)
- [ ] API key authentication works via X-API-Key header on /usage endpoint
- [ ] Invalid API key returns 401

---

## Feature Verification Tips

### Mock Implementations

Several features use mock implementations that return realistic but deterministic data:

1. **Domain Verification** (`POST /sites/{id}/verify`): Always succeeds. Sets `verification_method="mock_verification"`.
2. **AI Blog Generation** (`POST /blog-posts/generate`): Generates placeholder content based on the post title and keywords. Content includes headings, bullet points, and SEO-friendly structure.
3. **Keyword Rank Refresh** (`POST /keywords/refresh`): Assigns random ranks (1-100), search volumes (100-50000), and difficulty scores (10.0-90.0). Preserves `previous_rank` for trend tracking.
4. **SEO Audits** (`POST /audits/run`): Randomly selects from 12 issue templates and 12 recommendation templates. Score is calculated based on issue severity (critical: -15, warning: -5).

### Plan Limit Enforcement

Test plan limits by creating a free-tier user and attempting to exceed:
- **Blog posts**: Free tier allows 2 posts/month. The 3rd creation should return 403.
- **Keywords**: Free tier allows 20 total keywords. The 21st should return 403.

### Cross-User Isolation

Every resource (sites, posts, keywords, audits, schema configs) is scoped to the owning user. Accessing another user's resource always returns 404 (not 403) to avoid leaking existence information.

### Stripe Mock Mode

When `STRIPE_SECRET_KEY` is empty, the billing system operates in mock mode:
- Checkout creates a mock subscription directly in the database.
- No real Stripe API calls are made.
- Webhooks accept raw JSON without signature verification.
