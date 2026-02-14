# ContentForge API Reference

> Part of [ContentForge](README.md) documentation

Complete endpoint reference for the ContentForge content generation API.

---

## Conventions

| Item | Detail |
|------|--------|
| **Base URL** | `http://localhost:8102/api/v1` |
| **Interactive docs** | `http://localhost:8102/docs` (Swagger UI) |
| **IDs** | UUID v4 strings |
| **Timestamps** | ISO 8601 UTC (`2026-02-14T10:30:00Z`) |
| **Pagination** | `?page=1&per_page=20` on list endpoints; response includes `items`, `total`, `page`, `per_page` |

### Authentication

| Method | Header | Use Case |
|--------|--------|----------|
| JWT Bearer | `Authorization: Bearer <token>` | Dashboard / user requests |
| API Key | `X-API-Key: cf_live_<key>` | Programmatic / server-to-server |

Obtain tokens via `/auth/login` or `/auth/register`. Create API keys via `POST /api-keys` after JWT auth.

**Public endpoints (no auth):** `/auth/register`, `/auth/login`, `/auth/refresh`, `/billing/plans`, `/health`

**Dual-auth endpoints (JWT or API Key):** `/auth/provision`, `/usage`

### Error Format

All errors return `{"detail": "message"}`. Validation errors (422) return an array of field-level details with `loc`, `msg`, and `type`.

### Status Codes

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

## Auth (`/auth`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/auth/register` | None | 201 | Create account; returns access + refresh tokens and user object |
| POST | `/auth/login` | None | 200 | Authenticate; returns same format as register |
| POST | `/auth/refresh` | None | 200 | Exchange refresh token for new token pair |
| GET | `/auth/me` | JWT | 200 | Current user profile (id, email, plan) |
| POST | `/auth/provision` | API Key | 201 | Platform-initiated user provisioning; returns user + API key |

### Auth Notes

- **Register/Login response:** `access_token`, `refresh_token`, `token_type` ("bearer"), and `user` object with `id`, `email`, `plan`, `created_at`.
- **Register request:** `email` (unique), `password` (min 8 chars).
- **Refresh request:** `refresh_token` string. Returns new token pair.
- **Provision request:** `email`, `external_platform_id`, `external_store_id`, `plan`. Returns `user` object and `api_key`.
- **Key errors:** 409 duplicate email on register, 401 invalid credentials on login, 422 password < 8 chars.

---

## Content Generation (`/content`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/content/generate` | JWT | 201 | Create a single generation job |
| POST | `/content/generate/bulk` | JWT | 201 | Bulk generate from multiple URLs (Pro/Enterprise) |
| GET | `/content/jobs` | JWT | 200 | List generation jobs (paginated) |
| GET | `/content/jobs/{id}` | JWT | 200 | Get job with all content items and images |
| DELETE | `/content/jobs/{id}` | JWT | 204 | Delete job and all associated content/images |
| PATCH | `/content/{content_id}` | JWT | 200 | Edit generated content text (increments version) |

### Generate Request Fields

- `source_type` -- `url` or `csv` (required)
- `source_url` -- URL to scrape product data from (required for `url` type)
- `template_id` -- UUID of template to use (optional, defaults to system template)
- `content_types` -- Array of types to generate: `title`, `description`, `meta_description`, `keywords`, `bullet_points`
- `image_urls` -- Array of image URLs to process and optimize (optional)

### Generate Response

Returns the job object with:
- `id`, `user_id`, `source_type`, `source_url`, `status` (completed/failed/pending)
- `content_items` -- Array of `{id, content_type, content, word_count}`
- `image_items` -- Array of `{id, original_url, format, status}`

### Bulk Generate

`POST /content/generate/bulk` accepts `urls` array and optional `template_id`. Returns `jobs` array with one job per URL. Requires Pro or Enterprise plan.

### Content Edit

`PATCH /content/{content_id}` accepts `{"content": "new text"}`. Returns updated item with incremented `version` and recalculated `word_count`.

### Plan Limits

| Plan | Generations/mo | Images/mo |
|------|---------------|-----------|
| Free | 10 | 5 |
| Pro | 200 | 100 |
| Enterprise | Unlimited | Unlimited |

Returns 403 when monthly limit is exceeded.

---

## Templates (`/templates`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/templates/` | JWT | 201 | Create custom template |
| GET | `/templates/` | JWT | 200 | List system + user templates |
| GET | `/templates/{id}` | JWT | 200 | Get template details |
| PATCH | `/templates/{id}` | JWT | 200 | Update custom template (partial) |
| DELETE | `/templates/{id}` | JWT | 204 | Delete custom template |

### Template Fields

- `name` -- Template display name
- `description` -- What this template is for
- `tone` -- Writing tone: `professional`, `casual`, `playful`, `formal`, etc.
- `style` -- Output style: `detailed`, `concise`, `bullet_points`, etc.
- `content_types` -- Which content types this template supports
- `prompt_override` -- Optional custom AI prompt for full control
- `is_system` -- Boolean, read-only (true for built-in templates)

### System Templates

Built-in templates (e.g. "Professional", "Casual", "SEO-Optimized") have `is_system: true` and cannot be updated or deleted (returns 403).

User isolation applies -- list endpoint returns all system templates plus the authenticated user's custom templates only.

---

## Images (`/images`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/images/` | JWT | 200 | List processed images (paginated) |
| GET | `/images/{id}` | JWT | 200 | Get single image details |
| DELETE | `/images/{id}` | JWT | 204 | Delete image record (does not delete parent job) |

### Image Fields

- `original_url` -- Source image URL
- `format` -- Output format (default: `webp`)
- `width`, `height` -- Dimensions in pixels
- `size_bytes` -- Optimized file size
- `status` -- Processing status: `completed`, `failed`, `pending`
- `job_id` -- UUID of the parent generation job

Deleting an image does not affect its parent job or sibling content items.

---

## Billing (`/billing`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/billing/plans` | None | 200 | List all plan tiers with pricing |
| POST | `/billing/checkout` | JWT | 201 | Create Stripe checkout session |
| POST | `/billing/portal` | JWT | 200 | Create Stripe customer portal session |
| GET | `/billing/current` | JWT | 200 | Current subscription or null |
| GET | `/billing/overview` | JWT | 200 | Full billing overview with usage metrics |

### Plan Tiers

| Plan | Price | Generations | Images | API Access |
|------|-------|-------------|--------|------------|
| Free | $0/mo | 10 | 5 | No |
| Pro | $19/mo | 200 | 100 | Yes |
| Enterprise | $49/mo | Unlimited | Unlimited | Yes |

**Checkout:** Creates a Stripe checkout session. Returns `checkout_url` and `session_id`. Errors: 400 for free tier or duplicate subscription.

**Portal:** Returns `portal_url` for managing existing Stripe subscriptions.

**Overview:** Returns `current_plan`, `plan_name`, `subscription` object, and `usage` with `generations_used`/`generations_limit` and `images_used`/`images_limit`.

---

## API Keys (`/api-keys`)

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/api-keys` | JWT | 201 | Create API key (raw key returned once) |
| GET | `/api-keys` | JWT | 200 | List keys (prefix only, no raw keys) |
| DELETE | `/api-keys/{id}` | JWT | 204 | Revoke API key |

### API Key Notes

- Key prefix: `cf_live_`. The full raw key is only returned in the create response -- store it securely.
- List endpoint returns `id`, `name`, `key_prefix`, `is_active`, `created_at` (no raw keys).
- Revoked keys are marked inactive and can no longer authenticate requests.

---

## Usage & Health

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| GET | `/usage` | JWT or API Key | 200 | Current period usage metrics (generations, images) |
| GET | `/health` | None | 200 | Service health check (`service`, `status`) |

**Usage response:** `period_start`, `period_end`, and `metrics` array with `{name, used, limit}` entries for `generations` and `images`.

---

## Webhooks

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | `/webhooks/stripe` | Stripe signature | 200 | Handles subscription lifecycle events |

Supported events: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`.

Webhook signature is verified via the `Stripe-Signature` header and `STRIPE_WEBHOOK_SECRET` environment variable.

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md) · [README](README.md)*
