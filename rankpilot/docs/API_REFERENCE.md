# RankPilot API Reference

> Part of [RankPilot](README.md) documentation

## Base URL

```
http://localhost:8103/api/v1
```

Interactive docs: [Swagger UI](http://localhost:8103/docs) | [ReDoc](http://localhost:8103/redoc)

## Authentication

All protected endpoints require one of:

- **Bearer JWT:** `Authorization: Bearer <access_token>` -- obtained from `/auth/register` or `/auth/login`. Access tokens expire after 30 minutes; refresh tokens after 7 days.
- **API Key:** `X-API-Key: <raw_key>` -- available for Pro/Enterprise plans. Created via `POST /api-keys`.

## API Conventions

**Pagination** -- All list endpoints return `{ "items": [...], "total": N, "page": 1, "per_page": 20 }`. Query with `page` (default 1) and `per_page` (default 20, max 100).

**Errors** -- All errors return `{ "detail": "message" }`.

| Code | Meaning |
|------|---------|
| 400 | Bad request / duplicate resource |
| 401 | Not authenticated |
| 403 | Plan limit reached |
| 404 | Not found / not owned by user |
| 409 | Conflict (duplicate email) |
| 422 | Pydantic validation failure |

**Sentinel pattern for updates** -- Field omitted = no change; field set to `null` = clear; field set to value = update.

**Plan limits:**

| Tier | Blog Posts/Month | Keywords | Sites | API Access |
|------|-----------------|----------|-------|------------|
| Free | 2 | 20 | 1 | No |
| Pro | 20 | 200 | 5 | Yes |
| Enterprise | Unlimited | Unlimited | Unlimited | Yes |

## Endpoints

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Returns `{ "status": "ok", "service": "rankpilot", "timestamp": "..." }` |

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register user. Returns tokens. Errors: 409 (duplicate email), 422 (short password) |
| POST | `/auth/login` | No | Login. Returns tokens. Errors: 401 (invalid credentials) |
| POST | `/auth/refresh` | No | Refresh access token. Body: `{ "refresh_token": "..." }`. Errors: 401 |
| GET | `/auth/me` | JWT | Get authenticated user profile (id, email, plan, is_active, created_at) |
| POST | `/auth/provision` | JWT/Key | Provision user from platform. Body includes email, password, plan, external IDs. Returns user_id + api_key |

### Sites

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/sites` | JWT | Create site. Body: `{ "domain", "sitemap_url" }`. Errors: 400 (duplicate), 422 (domain < 3 chars) |
| GET | `/sites` | JWT | List sites (paginated) |
| GET | `/sites/{site_id}` | JWT | Get site by ID. Errors: 404 |
| PATCH | `/sites/{site_id}` | JWT | Update site fields (domain, sitemap_url, status). All optional |
| DELETE | `/sites/{site_id}` | JWT | Delete site and all related data. Returns 204 |
| POST | `/sites/{site_id}/verify` | JWT | Verify domain ownership (mock). Sets is_verified=true, status=active |

### Blog Posts

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/blog-posts` | JWT | Create blog post. Body: `{ site_id, title, content?, meta_description?, keywords?, status? }`. Errors: 403 (limit), 404 (site) |
| GET | `/blog-posts` | JWT | List posts (paginated). Filter: `site_id` (optional) |
| GET | `/blog-posts/{post_id}` | JWT | Get post by ID. Errors: 404 |
| PATCH | `/blog-posts/{post_id}` | JWT | Update post fields. Setting status to "published" auto-sets published_at |
| DELETE | `/blog-posts/{post_id}` | JWT | Delete post. Returns 204 |
| POST | `/blog-posts/generate` | JWT | Generate AI content for post. Body: `{ "post_id": "uuid" }`. Errors: 404 |

Auto-generated fields: `slug` (from title), `word_count` (from content).

### Keywords

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/keywords` | JWT | Add keyword. Body: `{ site_id, keyword }`. Errors: 400 (duplicate), 403 (limit), 404 (site) |
| GET | `/keywords` | JWT | List keywords. Required filter: `site_id`. Returns current_rank, previous_rank, search_volume, difficulty |
| DELETE | `/keywords/{keyword_id}` | JWT | Remove keyword. Required query: `site_id`. Errors: 404 |
| POST | `/keywords/refresh` | JWT | Refresh rank data for all keywords in site. Body: `{ "site_id" }`. Returns updated_count |

### SEO Audits

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/audits/run` | JWT | Run SEO audit (mock). Body: `{ "site_id" }`. Returns overall_score, issues[], recommendations[], pages_crawled |
| GET | `/audits` | JWT | List audit history. Required filter: `site_id` (paginated) |
| GET | `/audits/{audit_id}` | JWT | Get single audit result. Errors: 404 |

Issues include severity (critical/warning/info), category, and message.

### Schema Markup

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/schema` | JWT | Create JSON-LD config. Body: `{ site_id, page_type, schema_json? }`. Supported types: product, article, faq, breadcrumb, organization. Omitting schema_json generates a default template |
| GET | `/schema` | JWT | List schema configs. Required filter: `site_id` (paginated) |
| GET | `/schema/{config_id}` | JWT | Get schema config by ID |
| PATCH | `/schema/{config_id}` | JWT | Update schema_json or is_active |
| DELETE | `/schema/{config_id}` | JWT | Delete schema config. Returns 204 |
| GET | `/schema/{config_id}/preview` | JWT | Preview rendered `<script type="application/ld+json">` tag. Returns text/plain |

### Billing

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/billing/plans` | No | List all plan tiers with pricing and features |
| POST | `/billing/checkout` | JWT | Create Stripe checkout session. Body: `{ "plan": "pro" }`. Errors: 400 (free plan or already subscribed) |
| POST | `/billing/portal` | JWT | Create Stripe customer portal session. Returns portal_url |
| GET | `/billing/current` | JWT | Get current subscription (returns null if none) |
| GET | `/billing/overview` | JWT | Full billing dashboard: current_plan, price, usage (blog_posts_this_month, total_keywords vs limits) |

### API Keys

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api-keys` | JWT | Create API key (Pro/Enterprise only). Body: `{ name, scopes }`. Raw key shown once in response |
| GET | `/api-keys` | JWT | List API keys (without raw key values) |
| DELETE | `/api-keys/{key_id}` | JWT | Revoke (deactivate) API key. Returns 204 |

### Usage

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/usage` | JWT/Key | Current billing period usage: blog_posts_this_month, total_keywords |

### Webhooks

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/webhooks/stripe` | Stripe Sig | Handle Stripe webhook events. Supported: `customer.subscription.created`, `.updated`, `.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed` |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md)*
