# PostPilot API Reference

> Part of [PostPilot](README.md) documentation

## Base URL

- **Development:** `http://localhost:8106/api/v1`
- **Production:** Set via `NEXT_PUBLIC_API_URL`

## Authentication

- **Bearer JWT:** `Authorization: Bearer <access_token>` -- obtained from `/auth/login` or `/auth/register`.
- **API Key:** `X-API-Key: po_live_<token>` -- available on Pro/Enterprise plans.

## API Conventions

**Pagination** -- List endpoints return `{ "items": [...], "total": N, "page": 1, "per_page": 10 }`. Query with `page` and `per_page`.

**Errors** -- All errors return `{ "detail": "message" }`.

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (delete) |
| 400 | Bad request / invalid state transition |
| 401 | Unauthorized |
| 403 | Plan limit reached |
| 404 | Not found |
| 409 | Conflict (duplicate email) |
| 422 | Pydantic validation error |

## Endpoints

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Returns `{ "status": "ok", "service": "PostPilot", "timestamp": "..." }` |

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register user. Returns tokens + user object. Errors: 409 (duplicate email), 422 (short password) |
| POST | `/auth/login` | No | Login. Returns tokens + user object. Errors: 401 (invalid credentials) |
| POST | `/auth/refresh` | No | Refresh access token. Body: `{ "refresh_token": "..." }`. Errors: 401 |
| GET | `/auth/me` | JWT/Key | Get current user profile (id, email, plan, created_at) |
| POST | `/auth/provision` | Key | Provision user from platform. Body: email, external IDs, plan. Returns user_id + api_key |

### Social Accounts

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/accounts` | JWT | Connect social account. Body: `{ platform, account_name, account_id_external? }`. Platforms: instagram, facebook, tiktok. Errors: 403 (limit), 422 (invalid platform/empty name) |
| GET | `/accounts` | JWT | List all social accounts (connected and disconnected) |
| DELETE | `/accounts/{account_id}` | JWT | Disconnect account (soft delete -- sets is_connected=false). Returns updated account. Errors: 404 |

### Posts

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/posts` | JWT | Create post. Body: `{ account_id, content, platform, media_urls?, hashtags?, scheduled_for? }`. Status is "draft" without scheduled_for, "scheduled" with it. Errors: 403 (limit), 422 |
| GET | `/posts` | JWT | List posts (paginated). Filters: `status` (draft/scheduled/posted/failed), `platform` |
| GET | `/posts/calendar` | JWT | Calendar view. Required: `start_date`, `end_date` (YYYY-MM-DD). Returns `{ days: [{ date, posts }], total_posts }` |
| GET | `/posts/{post_id}` | JWT | Get post by ID. Errors: 404 |
| PATCH | `/posts/{post_id}` | JWT | Update post (draft/scheduled only). Body: content?, hashtags?, scheduled_for?. Errors: 400 (posted/failed), 404 |
| DELETE | `/posts/{post_id}` | JWT | Delete post (draft/scheduled only). Returns 204. Errors: 400 (posted), 404 |
| POST | `/posts/{post_id}/schedule` | JWT | Schedule a draft. Body: `{ "scheduled_for": "ISO8601" }`. Errors: 400 (past time), 404 |

### Content Queue

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/queue` | JWT | Add product to queue. Body: `{ product_data: { title, description, price?, image_url? }, platforms: [...] }`. Status starts as "pending" |
| GET | `/queue` | JWT | List queue items (paginated). Filter: `status` (pending/approved/rejected/posted) |
| GET | `/queue/{item_id}` | JWT | Get queue item. Errors: 404 |
| DELETE | `/queue/{item_id}` | JWT | Delete queue item (pending/rejected only). Returns 204. Errors: 400 (approved/posted), 404 |
| POST | `/queue/{item_id}/generate` | JWT | Generate AI caption for item. Updates ai_generated_content. Errors: 404 |
| POST | `/queue/{item_id}/approve` | JWT | Approve item (pending only). Errors: 400 (wrong status), 404 |
| POST | `/queue/{item_id}/reject` | JWT | Reject item (pending only). Errors: 400 (wrong status), 404 |
| POST | `/queue/generate-caption` | JWT | Generate caption without queue. Body: `{ product_data, platform, tone }`. Returns `{ caption, hashtags, platform }` |

### Analytics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/analytics/overview` | JWT | Aggregated metrics: total_posts, impressions, reach, likes, comments, shares, clicks, avg_engagement_rate |
| GET | `/analytics/posts` | JWT | Per-post metrics (paginated): impressions, reach, likes, comments, shares, clicks, engagement_rate |
| GET | `/analytics/posts/{post_id}` | JWT | Metrics for a specific post. Errors: 404 |

### Billing

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/billing/plans` | No | List plan tiers with pricing and features |
| POST | `/billing/checkout` | JWT | Create Stripe checkout session. Body: `{ "plan": "pro" }`. Errors: 400 (free plan or duplicate) |
| GET | `/billing/current` | JWT | Current subscription (returns null if none) |
| GET | `/billing/overview` | JWT | Full billing data: current_plan, subscription, usage (posts_this_month/limit, connected_accounts/limit) |

### API Keys

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api-keys` | JWT | Create API key. Body: `{ "name": "..." }`. Raw key shown once in response |
| GET | `/api-keys` | JWT | List API keys (no raw values) |
| DELETE | `/api-keys/{key_id}` | JWT | Revoke API key. Returns 204. Errors: 404 |

### Usage

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/usage` | JWT/Key | Current usage: posts_this_month, posts_limit, connected_accounts, accounts_limit |

## Common Error Patterns

| Status | When | Detail |
|--------|------|--------|
| 401 | Missing/invalid auth | `"Not authenticated"` or `"Invalid or expired token"` |
| 403 | Plan limit | `"Account limit reached..."` or `"Monthly post limit reached..."` |
| 404 | Resource not found | `"Post not found"`, `"Account not found"`, `"Queue item not found"` |
| 400 | Invalid transition | `"Cannot approve item with status 'approved'"`, `"Cannot delete approved or posted items"` |
| 400 | Past schedule | `"Cannot schedule a post in the past"` |
| 400 | Update immutable | `"Cannot update a post that has been posted or failed"` |
| 409 | Duplicate email | `"A user with this email already exists"` |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md) · [README](README.md)*
