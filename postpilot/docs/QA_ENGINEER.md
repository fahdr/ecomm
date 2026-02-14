# QA Engineer Guide

**For QA Engineers:** This guide covers the complete testing infrastructure, API endpoint inventory, verification checklists, and quality assurance procedures for PostPilot -- the Social Media Automation service. PostPilot manages social account connections, post creation and scheduling, AI-powered content generation, and engagement analytics across Instagram, Facebook, and TikTok.

---

## Test Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Test Framework | pytest + pytest-asyncio | Async test support for FastAPI |
| HTTP Client | httpx.AsyncClient | In-process ASGI testing (no network) |
| Database | PostgreSQL 16 | Same instance, tables truncated between tests |
| Stripe | Mock mode | `STRIPE_SECRET_KEY` is empty -- no real API calls |
| AI Generation | Mock mode | Template-based captions, no real LLM calls |

---

## Running Tests

### Commands

```bash
# Run all 157 backend tests
make test-backend

# Verbose output with test names
cd backend && pytest -v

# Run a specific test file
cd backend && pytest tests/test_posts.py -v

# Run a single test by name
cd backend && pytest tests/test_queue.py::test_generate_caption_for_queue_item -v

# Run tests matching a keyword
cd backend && pytest -k "calendar" -v

# Show test durations
cd backend && pytest --durations=10
```

### Test Count: 157 Total

| Test File | Count | Coverage Area |
|-----------|-------|---------------|
| `test_queue.py` | 22 | Content queue CRUD, AI caption generation, approve/reject workflow, status transitions, deletion rules, user isolation |
| `test_posts.py` | 20 | Post CRUD, draft vs scheduled creation, pagination, status/platform filtering, update, delete, scheduling, calendar view, user isolation |
| `test_accounts.py` | 16 | Social account connect (all 3 platforms), list, disconnect, auto-generated external IDs, validation (invalid platform, empty name), user isolation |
| `test_auth.py` | 10 | Registration, duplicate email (409), short password (422), login, wrong password (401), nonexistent user, token refresh, invalid refresh token, profile, unauthenticated profile |
| `test_billing.py` | 9 | Plan listing, pricing details, checkout (pro), checkout free fails (400), duplicate subscription (400), billing overview, overview after subscribe, current subscription (null), current subscription after subscribe |
| `test_api_keys.py` | 5 | Key creation (raw key returned), listing (no raw keys), revocation, auth via X-API-Key, invalid API key (401) |
| `test_health.py` | 1 | Health check returns status, service name, timestamp |
| `test_platform_webhooks.py` | -- | Platform event webhook handling |

---

## Test Structure

### Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Single event loop for all tests |
| `setup_db` | function (autouse) | Creates tables before test, truncates all tables + terminates other DB connections after each test |
| `db` | function | Raw async database session |
| `client` | function | `httpx.AsyncClient` configured against the FastAPI app |
| `auth_headers` | function | Registers a fresh user and returns `{"Authorization": "Bearer <token>"}` |

### Helper: `register_and_login(client, email=None)`

Registers a user with a random email (or specified one) and returns auth headers. Used in tests that need multiple isolated users for user isolation verification.

---

## API Documentation

### Interactive Docs

- **Swagger UI**: http://localhost:8106/docs
- **ReDoc**: http://localhost:8106/redoc
- **OpenAPI JSON**: http://localhost:8106/openapi.json

---

## Endpoint Summary

### Auth (`/api/v1/auth`)

| Method | Path | Status | Description | Auth |
|--------|------|--------|-------------|------|
| POST | `/auth/register` | 201 | Register new user, returns tokens | No |
| POST | `/auth/login` | 200 | Login with email/password | No |
| POST | `/auth/refresh` | 200 | Refresh expired access token | No |
| GET | `/auth/me` | 200 | Get user profile | JWT |
| POST | `/auth/forgot-password` | 200 | Request password reset (stub) | No |
| POST | `/auth/provision` | 201 | Provision user from platform | API Key |

### Social Accounts (`/api/v1/accounts`)

| Method | Path | Status | Description | Auth |
|--------|------|--------|-------------|------|
| POST | `/accounts` | 201 | Connect social account (Instagram/Facebook/TikTok) | JWT |
| GET | `/accounts` | 200 | List all connected accounts | JWT |
| DELETE | `/accounts/{account_id}` | 200 | Disconnect account (soft delete) | JWT |

### Posts (`/api/v1/posts`)

| Method | Path | Status | Description | Auth |
|--------|------|--------|-------------|------|
| POST | `/posts` | 201 | Create post (draft or scheduled) | JWT |
| GET | `/posts` | 200 | List posts with pagination + filters | JWT |
| GET | `/posts/calendar` | 200 | Calendar view (grouped by date) | JWT |
| GET | `/posts/{post_id}` | 200 | Get single post | JWT |
| PATCH | `/posts/{post_id}` | 200 | Update post (draft/scheduled only) | JWT |
| DELETE | `/posts/{post_id}` | 204 | Delete post (draft/scheduled only) | JWT |
| POST | `/posts/{post_id}/schedule` | 200 | Schedule post for future publication | JWT |

### Content Queue (`/api/v1/queue`)

| Method | Path | Status | Description | Auth |
|--------|------|--------|-------------|------|
| POST | `/queue` | 201 | Add product to content queue | JWT |
| GET | `/queue` | 200 | List queue items with pagination + status filter | JWT |
| GET | `/queue/{item_id}` | 200 | Get single queue item | JWT |
| DELETE | `/queue/{item_id}` | 204 | Delete queue item (pending/rejected only) | JWT |
| POST | `/queue/{item_id}/generate` | 200 | Generate AI caption for queue item | JWT |
| POST | `/queue/{item_id}/approve` | 200 | Approve item (pending only) | JWT |
| POST | `/queue/{item_id}/reject` | 200 | Reject item (pending only) | JWT |
| POST | `/queue/generate-caption` | 200 | Standalone caption generation (no persistence) | JWT |

### Analytics (`/api/v1/analytics`)

| Method | Path | Status | Description | Auth |
|--------|------|--------|-------------|------|
| GET | `/analytics/overview` | 200 | Aggregated metrics across all posts | JWT |
| GET | `/analytics/posts` | 200 | Metrics for all published posts (paginated) | JWT |
| GET | `/analytics/posts/{post_id}` | 200 | Metrics for a single post | JWT |

### Billing (`/api/v1/billing`)

| Method | Path | Status | Description | Auth |
|--------|------|--------|-------------|------|
| GET | `/billing/plans` | 200 | List all plan tiers | No |
| POST | `/billing/checkout` | 201 | Create Stripe checkout session | JWT |
| POST | `/billing/portal` | 200 | Create Stripe customer portal session | JWT |
| GET | `/billing/current` | 200 | Get current subscription (or null) | JWT |
| GET | `/billing/overview` | 200 | Full billing overview with usage metrics | JWT |

### API Keys (`/api/v1/api-keys`)

| Method | Path | Status | Description | Auth |
|--------|------|--------|-------------|------|
| POST | `/api-keys` | 201 | Create API key (raw key returned once) | JWT |
| GET | `/api-keys` | 200 | List all keys (no raw key values) | JWT |
| DELETE | `/api-keys/{key_id}` | 204 | Revoke (deactivate) an API key | JWT |

### System

| Method | Path | Status | Description | Auth |
|--------|------|--------|-------------|------|
| GET | `/api/v1/health` | 200 | Health check with service metadata | No |
| GET | `/api/v1/usage` | 200 | Current usage metrics | JWT or API Key |
| POST | `/api/v1/webhooks/stripe` | 200 | Stripe webhook handler | Stripe signature |

---

## Verification Checklist

### Authentication

- [ ] Register with valid email/password returns 201 with access + refresh tokens
- [ ] Register with duplicate email returns 409
- [ ] Register with short password (< 8 chars) returns 422
- [ ] Login with correct credentials returns 200 with tokens
- [ ] Login with wrong password returns 401
- [ ] Login with nonexistent email returns 401
- [ ] Refresh with valid refresh token returns new token pair
- [ ] Refresh with access token (not refresh type) returns 401
- [ ] GET /auth/me with valid token returns user profile
- [ ] GET /auth/me without token returns 401
- [ ] Token `type` field distinguishes access vs refresh tokens

### Social Accounts

- [ ] Connect Instagram account returns 201 with `is_connected=true`
- [ ] Connect Facebook account returns 201 with correct platform
- [ ] Connect TikTok account returns 201 with correct platform
- [ ] Connect without `account_id_external` auto-generates one
- [ ] Connect with invalid platform ("myspace") returns 422
- [ ] Connect with empty account name returns 422
- [ ] Connect without auth returns 401
- [ ] List accounts returns empty array for new user
- [ ] List accounts returns all connected accounts
- [ ] List accounts shows disconnected accounts with `is_connected=false`
- [ ] Disconnect account returns 200 with `is_connected=false`
- [ ] Disconnect preserves account in list (soft delete)
- [ ] Disconnect nonexistent account returns 404
- [ ] User B cannot see or disconnect user A's accounts
- [ ] Plan limit enforcement: free tier limited to 1 connected account

### Posts

- [ ] Create post without `scheduled_for` creates a draft (status=draft)
- [ ] Create post with `scheduled_for` creates scheduled post
- [ ] Create with only required fields (account_id, content, platform) returns 201
- [ ] Create with empty content returns 422
- [ ] Create without auth returns 401
- [ ] List posts returns paginated response `{ items, total, page, per_page }`
- [ ] Pagination respects `page` and `per_page` parameters
- [ ] Filter by `status=draft` returns only draft posts
- [ ] Filter by `platform=instagram` returns only Instagram posts
- [ ] Get post by ID returns 200 with correct data
- [ ] Get nonexistent post returns 404
- [ ] Update draft post content returns 200 with updated content
- [ ] Update hashtags independently returns 200
- [ ] Update nonexistent post returns 404
- [ ] Delete draft post returns 204 and post is removed
- [ ] Delete nonexistent post returns 404
- [ ] Delete without auth returns 401
- [ ] Schedule draft post with future time returns 200 with status=scheduled
- [ ] Schedule with past time returns 400
- [ ] Schedule nonexistent post returns 404
- [ ] Calendar view returns posts grouped by date within range
- [ ] Calendar view with no scheduled posts returns `total_posts=0`
- [ ] Calendar without required date params returns 422
- [ ] User B cannot see user A's posts
- [ ] Plan limit enforcement: free tier limited to 10 posts/month

### Content Queue

- [ ] Create queue item returns 201 with status=pending
- [ ] Created item has `ai_generated_content=null`
- [ ] Empty platforms list is accepted
- [ ] Create without auth returns 401
- [ ] List queue items returns paginated response
- [ ] Pagination works correctly
- [ ] Filter by status=pending returns only pending items
- [ ] Filter by status=approved with no approved items returns total=0
- [ ] List without auth returns 401
- [ ] Get single queue item by ID returns 200
- [ ] Get nonexistent item returns 404
- [ ] User B cannot access user A's queue items
- [ ] Generate AI caption populates `ai_generated_content` (non-null, non-empty)
- [ ] Generate for nonexistent item returns 404
- [ ] Standalone caption generation returns `{ caption, hashtags, platform }`
- [ ] Standalone with default platform uses "instagram"
- [ ] Approve pending item changes status to "approved"
- [ ] Approve already-approved item returns 400
- [ ] Approve nonexistent item returns 404
- [ ] Reject pending item changes status to "rejected"
- [ ] Reject already-rejected item returns 400
- [ ] Reject nonexistent item returns 404
- [ ] Delete pending item returns 204
- [ ] Delete rejected item returns 204 (allowed)
- [ ] Delete approved item returns 400 (not allowed)
- [ ] Delete nonexistent item returns 404

### Analytics

- [ ] Overview with no posts returns zero-filled metrics
- [ ] Overview with published posts returns aggregated totals
- [ ] Engagement rate formula: `(likes + comments + shares) / impressions * 100`
- [ ] Per-post metrics return correct values per post
- [ ] Metrics for nonexistent post returns 404

### Billing

- [ ] List plans returns 3 tiers (free, pro, enterprise)
- [ ] Free plan has `price_monthly_cents=0` and `trial_days=0`
- [ ] Checkout for pro plan returns 201 with checkout_url and session_id
- [ ] Checkout for free plan returns 400
- [ ] Duplicate subscription checkout returns 400
- [ ] Billing overview returns current plan, usage metrics
- [ ] Overview after subscribe reflects upgraded plan
- [ ] Current subscription returns null for new user
- [ ] Current subscription returns subscription data after checkout

### API Keys

- [ ] Create key returns 201 with raw key (visible only once)
- [ ] List keys returns metadata without raw key values
- [ ] Revoke key returns 204 and marks key as inactive
- [ ] Auth via X-API-Key header succeeds with valid key
- [ ] Auth via X-API-Key with invalid key returns 401

### Health

- [ ] GET /api/v1/health returns 200 with `{ status: "ok", service: "...", timestamp: "..." }`

---

## Feature Verification

### Post Lifecycle

Verify the full lifecycle from creation to analytics:

```
1. Register user (POST /auth/register)
2. Connect Instagram account (POST /accounts)
3. Create draft post (POST /posts) -- status=draft
4. Update post content (PATCH /posts/{id})
5. Schedule post (POST /posts/{id}/schedule) -- status=scheduled
6. Verify calendar shows the post (GET /posts/calendar)
7. [Celery publishes post] -- status=posted
8. Check analytics overview (GET /analytics/overview)
9. Check post metrics (GET /analytics/posts/{id})
```

### Content Queue Workflow

Verify the AI-assisted content pipeline:

```
1. Register + login
2. Add product to queue (POST /queue) -- status=pending
3. Generate AI caption (POST /queue/{id}/generate) -- ai_generated_content populated
4. Review caption content
5. Approve item (POST /queue/{id}/approve) -- status=approved
6. [Convert to scheduled post]
```

### Plan Upgrade Flow

Verify billing and plan enforcement:

```
1. Register (free plan by default)
2. Verify plan limits (10 posts/month, 1 account)
3. Create checkout for Pro (POST /billing/checkout)
4. Verify billing overview reflects Pro plan
5. Verify increased limits (200 posts/month, 10 accounts)
```

### Multi-User Isolation

Verify data isolation between users:

```
1. Register user A, create accounts + posts + queue items
2. Register user B
3. Verify user B sees empty lists for accounts, posts, queue
4. Verify user B gets 404 when accessing user A's resources by ID
```

---

## Common Error Patterns

| Status | When | Expected Detail |
|--------|------|-----------------|
| 401 | Missing auth token | `"Not authenticated"` |
| 401 | Invalid/expired token | `"Invalid or expired token"` |
| 401 | Invalid API key | `"Not authenticated. Provide a Bearer token or X-API-Key."` |
| 403 | Plan limit reached | `"Account limit reached (N accounts). Upgrade your plan..."` or `"Monthly post limit reached (N posts)..."` |
| 404 | Resource not found | `"Post not found"`, `"Account not found"`, `"Queue item not found"` |
| 400 | Invalid state transition | `"Cannot approve item with status 'approved'"`, `"Cannot delete approved or posted items"` |
| 400 | Past schedule time | `"Cannot schedule a post in the past"` |
| 400 | Update immutable post | `"Cannot update a post that has been posted or failed"` |
| 409 | Duplicate email | `"A user with this email already exists"` |
| 422 | Validation error | Pydantic validation details |

---

## Dashboard Pages to Test

| Page | Route | Key Interactions |
|------|-------|-----------------|
| Dashboard Home | `/` | KPI cards load, animated counters, quick action buttons |
| Accounts | `/accounts` | Connect dialog (3 platforms), disconnect, empty state |
| Queue | `/queue` | Add product dialog, generate caption, approve/reject, calendar sidebar |
| Posts | `/posts` | Post list, pagination, status/platform filters |
| Billing | `/billing` | Plan cards, checkout button, current plan display |
| API Keys | `/api-keys` | Create key, copy raw key, revoke key |
| Settings | `/settings` | User profile display |
| Login | `/login` | Email/password form, error states |
| Register | `/register` | Registration form, redirect on success |

### Dashboard UX Checks

- [ ] Loading skeletons appear before data loads
- [ ] Error state displays when API is unreachable
- [ ] Empty states show appropriate messaging with action buttons
- [ ] Animated counters count up to correct values
- [ ] Responsive layout collapses correctly on mobile widths
- [ ] Dark text on dark backgrounds does not occur (contrast check)
- [ ] All navigation items in sidebar route to real pages
