# API Reference

> Part of [Dropshipping Platform](README.md) documentation

## Interactive Documentation

| URL | Format |
|-----|--------|
| `http://localhost:8000/docs` | Swagger UI — interactive, try-it-out interface |
| `http://localhost:8000/redoc` | ReDoc — clean read-only documentation |
| `http://localhost:8000/openapi.json` | Raw OpenAPI 3.x schema |

## Conventions

- All endpoints prefixed with `/api/v1/`
- Auth header: `Authorization: Bearer <jwt>`
- Store-scoped routes: `/api/v1/stores/{store_id}/...`
- Public routes (no auth): `/api/v1/public/stores/{slug}/...`
- Customer auth routes: `/api/v1/customer/...` (customer JWT, not store-owner JWT)
- Export routes: `/api/v1/stores/{store_id}/orders/export?format=csv`
- Bridge routes: `/api/v1/bridge/...` (ServiceBridge activity and dispatch)
- Auto-generated docs at `/docs` and `/redoc`

## Response Format

### Paginated Response

```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "per_page": 20
}
```

### Key Patterns

- **Slug uniqueness:** Use `generate_unique_slug(exclude_id=)` to avoid self-collision on updates
- **Sentinel values:** Python `...` (Ellipsis) distinguishes "not provided" from `None` in updates
- **Soft-delete:** Stores use status-based soft-delete (`status=deleted`), not hard delete
- **Customer vs Owner auth:** Store owners use `get_current_user`; customers use `get_current_customer` with separate JWT tokens

## Auth Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/register` | No | Create account |
| `POST` | `/api/v1/auth/login` | No | Get JWT tokens |
| `POST` | `/api/v1/auth/refresh` | No | Refresh access token |
| `POST` | `/api/v1/auth/forgot-password` | No | Password reset |
| `GET` | `/api/v1/auth/me` | Bearer JWT | Current user profile |

## Store Management

| Method | Path | Auth |
|--------|------|------|
| `POST` | `/api/v1/stores` | Bearer JWT |
| `GET` | `/api/v1/stores` | Bearer JWT |
| `GET` | `/api/v1/stores/{id}` | Bearer JWT |
| `PATCH` | `/api/v1/stores/{id}` | Bearer JWT |
| `DELETE` | `/api/v1/stores/{id}` | Bearer JWT |

## Store-Scoped Resources

All resources follow CRUD pattern at `/api/v1/stores/{store_id}/{resource}`:

| Resource | Endpoints | Notes |
|----------|-----------|-------|
| Products | CRUD + variants, images, search | `?status=active&search=keyword` |
| Orders | List + detail + fulfill + notes | Status transitions: pending→paid→shipped→delivered |
| Categories | CRUD + nesting | Parent/child hierarchy |
| Discounts | CRUD + validate | Percentage or fixed amount |
| Reviews | CRUD + moderate | Rating 1-5, moderation status |
| Themes | CRUD + presets + blocks | 11 presets, 13 block types |
| Gift Cards | CRUD + redeem | Codes with balance tracking |
| Customers | List + export | Customer account management |
| Suppliers | CRUD | Auto-fulfillment source |
| Tax | CRUD | Per-region tax rules |
| Segments | CRUD | Customer segment definitions |
| Upsells | CRUD | Cross-sell and bundle rules |
| Teams | Invite + manage | Editor/viewer roles |
| Webhooks | CRUD | Store-level webhook configs |
| A/B Tests | CRUD | Experiment management |
| Notifications | List + mark read | Dashboard notifications |
| Analytics | Revenue, orders, products | Date-range queries |

## Export Endpoints

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/api/v1/stores/{id}/orders/export?format=csv` | Bearer JWT |
| `GET` | `/api/v1/stores/{id}/products/export?format=csv` | Bearer JWT |
| `GET` | `/api/v1/stores/{id}/customers/export?format=csv` | Bearer JWT |

## Public Storefront API

No authentication required. Sensitive fields (`user_id`, `cost`) excluded.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/public/stores/{slug}` | Store info |
| `GET` | `/api/v1/public/stores/{slug}/products` | Product listing |
| `GET` | `/api/v1/public/stores/{slug}/products/{slug}` | Product detail |
| `GET` | `/api/v1/public/stores/{slug}/categories` | Categories |
| `POST` | `/api/v1/public/stores/{slug}/checkout` | Create checkout |

## Customer Endpoints

Separate JWT tokens from store-owner tokens. Prefixed with `/api/v1/customer/`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/customer/register` | Customer registration |
| `POST` | `/api/v1/customer/login` | Customer login |
| `GET` | `/api/v1/customer/orders` | Order history |
| `GET/POST` | `/api/v1/customer/addresses` | Address book |
| `GET/POST` | `/api/v1/customer/wishlist` | Wishlist management |

## ServiceBridge Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/bridge/activity` | Paginated delivery log with filters |
| `GET` | `/api/v1/bridge/activity/{type}/{id}` | Per-resource deliveries |
| `GET` | `/api/v1/bridge/service/{name}/activity` | Per-service deliveries |
| `GET` | `/api/v1/bridge/summary` | 24h per-service summary |
| `POST` | `/api/v1/bridge/dispatch` | Manual event dispatch |

## Subscription Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/subscriptions/checkout` | Create Stripe checkout session |
| `POST` | `/api/v1/subscriptions/portal` | Create Stripe billing portal |
| `GET` | `/api/v1/subscriptions/current` | Current plan details |
| `POST` | `/api/v1/webhooks/stripe` | Stripe webhook handler |

---
*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md)*
