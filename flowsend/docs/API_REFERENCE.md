# FlowSend API Reference

> Part of [FlowSend](README.md) documentation

## Base URL & Docs

All endpoints prefixed with `/api/v1/`. Interactive docs at `/docs` (Swagger) and `/redoc`.

## Conventions

**Authentication** -- Two methods supported:
- JWT Bearer: `Authorization: Bearer <access_token>`
- API Key: `X-API-Key: <api_key>`

**Pagination** -- List endpoints accept `page` (default 1) and `page_size` (default 20, max 100). Response: `{ items, total, page, page_size }`.

**Errors** -- All errors return `{ "detail": "message" }`.

**DELETE** -- Returns `204 No Content` with empty body. Check `response.status === 204` before calling `.json()`.

| Code | Meaning |
|------|---------|
| 200 | OK (GET, PATCH, non-creation POST) |
| 201 | Created (POST resource creation) |
| 204 | No Content (DELETE) |
| 400 | Business logic error |
| 401 | Missing/invalid auth |
| 404 | Resource not found |
| 409 | Duplicate resource |
| 422 | Validation error |

## Auth Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | None | Register new user. Body: `{email, password}`. Returns tokens (201). Errors: 409 duplicate, 422 validation |
| POST | `/auth/login` | None | Login. Body: `{email, password}`. Returns tokens (200). Errors: 401 invalid |
| POST | `/auth/refresh` | None | Refresh tokens. Body: `{refresh_token}`. Returns new tokens (200) |
| GET | `/auth/me` | JWT | Get current user profile (200) |
| POST | `/auth/provision` | API Key | Cross-service user provisioning. Body: `{email, external_platform_id, external_store_id}`. Returns `{user_id, api_key}` (201) |

Token response format: `{ access_token, refresh_token, token_type: "bearer" }`

## Contact Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/contacts` | JWT | Create contact. Body: `{email, first_name?, last_name?, tags?, custom_fields?, is_subscribed?}`. Errors: 400 limit/duplicate, 422 invalid email |
| GET | `/contacts` | JWT | List contacts. Query: `page, page_size, search` (email ILIKE), `tag` |
| GET | `/contacts/{id}` | JWT | Get single contact |
| PATCH | `/contacts/{id}` | JWT | Update contact (all fields optional) |
| DELETE | `/contacts/{id}` | JWT | Delete contact (204) |
| POST | `/contacts/import` | JWT | Bulk import. Body: `{import_type: "email_list"|"csv", data, tags?}`. Returns `{imported, skipped, message}` |
| POST | `/contacts/lists` | JWT | Create contact list. Body: `{name, description?, list_type: "dynamic"|"static", rules?}` (201) |
| GET | `/contacts/lists` | JWT | List contact lists (paginated) |
| DELETE | `/contacts/lists/{id}` | JWT | Delete contact list (204) |

## Flow Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/flows` | JWT | Create flow. Body: `{name, description?, trigger_type, trigger_config?, steps?}`. Created as `draft` (201) |
| GET | `/flows` | JWT | List flows. Query: `page, page_size, status` (`draft`/`active`/`paused`) |
| GET | `/flows/{id}` | JWT | Get single flow |
| PATCH | `/flows/{id}` | JWT | Update flow. Errors: 400 cannot update active flow (pause first) |
| DELETE | `/flows/{id}` | JWT | Delete flow (204) |
| POST | `/flows/{id}/activate` | JWT | Activate flow. Errors: 400 if no steps |
| POST | `/flows/{id}/pause` | JWT | Pause flow. Errors: 400 if not active |
| GET | `/flows/{id}/executions` | JWT | List flow executions (paginated) |

**Trigger types:** `signup`, `purchase`, `abandoned_cart`, `custom`, `scheduled`

**Flow step types:** `email` with config `{template_id, delay_minutes}`

## Campaign Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/campaigns` | JWT | Create campaign. Body: `{name, subject, template_id, list_id, scheduled_at?}`. Status: `draft` or `scheduled` (201) |
| GET | `/campaigns` | JWT | List campaigns. Query: `page, page_size, status` (`draft`/`scheduled`/`sent`) |
| GET | `/campaigns/{id}` | JWT | Get single campaign |
| PATCH | `/campaigns/{id}` | JWT | Update campaign. Errors: 400 cannot update sent campaign |
| DELETE | `/campaigns/{id}` | JWT | Delete campaign. Errors: 400 cannot delete sent campaign (204) |
| POST | `/campaigns/{id}/send` | JWT | Send campaign. Creates mock EmailEvents for subscribed contacts. Errors: 400 already sent |
| GET | `/campaigns/{id}/analytics` | JWT | Campaign analytics. Returns `{sent, opened, clicked, bounced, open_rate, click_rate, bounce_rate}` |
| GET | `/campaigns/{id}/events` | JWT | List email events. Query: `event_type` (`sent`/`delivered`/`opened`/`clicked`/`bounced`/`unsubscribed`) |

## Template Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/templates` | JWT | Create template. Body: `{name, subject, html_content, text_content?, category}`. `is_system: false` (201) |
| GET | `/templates` | JWT | List templates. Query: `page, page_size, category`. Includes system + custom templates |
| GET | `/templates/{id}` | JWT | Get single template |
| PATCH | `/templates/{id}` | JWT | Update template. Errors: 400 cannot update system template |
| DELETE | `/templates/{id}` | JWT | Delete template. Errors: 400 cannot delete system template (204) |

**Categories:** `welcome`, `cart`, `promo`, `newsletter`, `transactional`

## Analytics Endpoint

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/analytics` | JWT | Aggregate analytics. Returns `{total_sent, total_opened, total_clicked, total_bounced, open_rate, click_rate, bounce_rate, campaigns[]}` |

## Billing Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/billing/plans` | None | List all plans with pricing. Price in cents; `-1` = unlimited |
| POST | `/billing/checkout` | JWT | Create Stripe checkout. Body: `{plan: "pro"|"enterprise"}`. Errors: 400 free/already subscribed |
| POST | `/billing/portal` | JWT | Create Stripe billing portal session |
| GET | `/billing/current` | JWT | Get current subscription (or `null`) |
| GET | `/billing/overview` | JWT | Billing overview with plan, subscription, and usage |

**Plans:** Free (500 emails/mo, 250 contacts, 2 flows), Pro ($39/mo, 25K emails, 10K contacts, 20 flows), Enterprise ($149/mo, unlimited).

## API Key Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api-keys` | JWT | Create API key. Body: `{name, scopes?}`. Returns full key once (201) |
| GET | `/api-keys` | JWT | List API keys (prefix only, no raw keys) |
| DELETE | `/api-keys/{id}` | JWT | Revoke API key (204) |

## Other Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Health check. Returns `{status, service, version}` |
| GET | `/usage` | JWT/API Key | Usage stats. Returns `{emails_sent, contacts, flows, campaigns}` |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md) · [README](README.md)*
