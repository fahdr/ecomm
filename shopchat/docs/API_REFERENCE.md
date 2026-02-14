# ShopChat API Reference

> Part of [ShopChat](README.md) documentation

## Base URL & Docs

All endpoints prefixed with `/api/v1/`. Interactive docs at `/docs` (Swagger UI) when the backend is running.

## Conventions

**Authentication** -- Three modes:
- JWT Bearer: `Authorization: Bearer <access_token>` (most endpoints)
- API Key: `X-API-Key: <api_key>` (programmatic access)
- None: Widget endpoints use `widget_key` to identify the chatbot

**Pagination** -- List endpoints accept `page` (default 1) and `page_size` (default 20). Response: `{ items, total, page, page_size }`.

**Errors** -- All errors return `{ "detail": "message" }`.

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 204 | No Content (DELETE) |
| 400 | Bad request / invalid input |
| 401 | Missing/invalid credentials |
| 403 | Plan limit exceeded |
| 404 | Resource not found |
| 409 | Duplicate resource |
| 422 | Validation error |
| 429 | Conversation limit exceeded |

## Auth Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | None | Register user. Body: `{email, password}`. Returns tokens (201). Errors: 409 duplicate, 422 short password |
| POST | `/auth/login` | None | Login. Body: `{email, password}`. Returns tokens (200). Errors: 401 invalid |
| POST | `/auth/refresh` | None | Refresh tokens. Body: `{refresh_token}`. Returns new tokens (200) |
| GET | `/auth/me` | JWT | Get current user profile (200) |
| POST | `/auth/provision` | API Key | Cross-service provisioning. Body: `{email, external_platform_id, external_store_id}`. Returns `{user_id, api_key}` (201) |

Token response format: `{ access_token, refresh_token, token_type: "bearer" }`

## Chatbot Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/chatbots` | JWT | Create chatbot. Body: `{name, personality?, welcome_message?, theme_config?}`. Returns chatbot with `widget_key` (201) |
| GET | `/chatbots` | JWT | List chatbots (paginated, user-scoped) |
| GET | `/chatbots/{id}` | JWT | Get chatbot detail. Errors: 404 |
| PATCH | `/chatbots/{id}` | JWT | Update chatbot (all fields optional) |
| DELETE | `/chatbots/{id}` | JWT | Delete chatbot + all associated data (cascade) (204) |

**Personality options:** `friendly`, `professional`, `casual`, `helpful`

**Theme config:** `{ primary_color, text_color, position, size }`

## Knowledge Base Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/knowledge` | JWT | Create entry. Body: `{chatbot_id, source_type, title, content, metadata?}`. Errors: 403 plan limit, 404 chatbot not found |
| GET | `/knowledge` | JWT | List entries. Query: `chatbot_id?, page, page_size` |
| GET | `/knowledge/{id}` | JWT | Get single entry. Errors: 404 |
| PATCH | `/knowledge/{id}` | JWT | Update entry (all fields optional) |
| DELETE | `/knowledge/{id}` | JWT | Delete entry (204) |

**Source types:** `product_catalog`, `policy_page`, `faq`, `custom_text`, `url`

## Conversation Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/conversations` | JWT | List conversations. Query: `chatbot_id?, page, page_size` |
| GET | `/conversations/{id}` | JWT | Get conversation detail with full message history |
| POST | `/conversations/{id}/end` | JWT | End conversation. Errors: 400 already ended |
| POST | `/conversations/{id}/rate` | JWT | Rate conversation. Body: `{score}` (1.0-5.0). Errors: 422 out of range |

Conversation detail includes `messages[]` with `{id, role, content, metadata, created_at}`. Assistant messages may include `product_suggestions` in metadata.

## Widget Endpoints (Public)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/widget/config/{widget_key}` | None | Get widget config (chatbot name, personality, theme). Errors: 404 inactive/not found |
| POST | `/widget/chat` | None | Send chat message. Body: `{widget_key, visitor_id, message, visitor_name?}`. Returns `{conversation_id, message, product_suggestions?}`. Errors: 404, 429 limit |

## Analytics Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/analytics/overview` | JWT | Aggregate stats: `{total_conversations, total_messages, avg_satisfaction, active_chatbots, conversations_today, top_chatbot_name}` |
| GET | `/analytics/chatbots` | JWT | Per-chatbot analytics: `{chatbot_id, chatbot_name, total_conversations, total_messages, avg_satisfaction, avg_messages_per_conversation}` |

## Billing Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/billing/plans` | None | List all plans with pricing. Price in cents; `-1` = unlimited |
| POST | `/billing/checkout` | JWT | Create Stripe checkout. Body: `{plan}`. Errors: 400 invalid/already subscribed |
| POST | `/billing/portal` | JWT | Create Stripe billing portal session |
| GET | `/billing/current` | JWT | Get current subscription (or `null`) |
| GET | `/billing/overview` | JWT | Billing overview with plan, subscription, and usage |

**Plans:** Free ($0, 50 conversations, 10 knowledge pages), Pro ($19/mo, 1K conversations, 500 pages), Enterprise ($79/mo, unlimited).

## API Key Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api-keys` | JWT | Create API key. Body: `{name}`. Full key returned once only (201) |
| GET | `/api-keys` | JWT | List API keys (prefix only) |
| DELETE | `/api-keys/{id}` | JWT | Revoke API key (204) |

## Other Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Health check. Returns `{status, service, version}` |
| GET | `/usage` | JWT/API Key | Usage stats with conversations and knowledge page counts |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md) · [README](README.md)*
