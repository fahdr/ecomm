# QA Engineer Guide

> Part of [Dropshipping Platform](README.md) documentation
>
> For test infrastructure, running tests, and coverage details, see [Testing Guide](TESTING.md).
> For API endpoints and schemas, see [API Reference](API_REFERENCE.md).

## ServiceBridge Acceptance Criteria

1. Creating a product fires `product.created` to 6 connected services
2. Updating a product fires `product.updated` to 3 services
3. Order fulfillment fires `order.shipped` to FlowSend
4. Customer registration fires `customer.created` to FlowSend
5. Each delivery is recorded with status, latency, error details
6. Dashboard activity page shows paginated delivery history
7. Filters (event, service, status) work correctly
8. Product/order detail pages show per-resource service status
9. Services hub shows health indicators per service
10. Manual dispatch endpoint fires event and returns confirmation

## ServiceBridge Edge Cases

- No connected services: event fires but nothing is delivered
- Service returns non-200: delivery recorded as failed with error
- Service times out: delivery recorded with timeout error
- Missing `platform_webhook_secret`: uses default dev secret
- Null `store_id`: supported for customer events (public endpoint)

## Seed Data & Demo Credentials

Before manual testing, seed the database:

```bash
cd /workspaces/ecomm && npx tsx scripts/seed.ts
```

| Role | Email | Password | URL |
|------|-------|----------|-----|
| **Store Owner** | `demo@example.com` | `password123` | Dashboard: `http://localhost:3000` |
| **Customer (Alice)** | `alice@example.com` | `password123` | Storefront: `http://localhost:3001?store=volt-electronics` |
| **Customer (Bob)** | `bob@example.com` | `password123` | Storefront |
| **Customer (Carol)** | `carol@example.com` | `password123` | Storefront |

### What to Verify After Seeding

| Feature | How to check |
|---------|-------------|
| Sale badges | Products page → ProBook, Galaxy Nova show "Sale" badge |
| New badges | Recently seeded products show "New" badge on storefront |
| Inventory alerts | Store overview → NovaBand, MagFloat show "Low Stock" warnings |
| Order lifecycle | Orders page → Alice (shipped), Bob (delivered), Carol & Dave (paid) |
| Order notes | Open any order → "Internal Notes" section has pre-filled notes |
| Theme blocks | Storefront homepage → hero, countdown, carousel, testimonials |
| Customer accounts | Log in as alice → account page shows addresses, wishlist, orders |
| Discount codes | WELCOME10, SUMMER25, FLAT20, AUDIO15, BIGSPEND50 |

## Verification Checklist

### Full Platform

```bash
# 1. Backend tests (580 should pass)
cd /workspaces/ecomm/dropshipping/backend && python -m pytest tests/ -x

# 2. Dashboard build
cd /workspaces/ecomm/dropshipping/dashboard && npm run build

# 3. Storefront build
cd /workspaces/ecomm/dropshipping/storefront && npm run build

# 4. E2E tests (200+ should pass)
cd /workspaces/ecomm/e2e && npx playwright test --reporter=line
```

### Phase 2 Polish Features

| Feature | How to verify |
|---------|--------------|
| Platform Home KPIs | Login → Dashboard home shows "Your Stores" with aggregate metrics |
| Store Overview KPIs | Navigate to store → see revenue, orders, products cards |
| Order Notes | Open order detail → "Internal Notes" textarea → type and blur → reload |
| CSV Export | Orders page + Products page → "Export CSV" button visible |
| Command Palette | Press `Ctrl+K` → search input → type to filter → Escape to close |
| Inventory Alerts | Create product with stock < 5 → store overview shows "Low Stock" |
| Theme Engine | Themes page → select preset → customize blocks → storefront reflects changes |
| Animations | Browse storefront → product grids animate with stagger → detail slides in |
| Product Badges | Recent products show "New"; products with compare_at_price show "Sale" |
| Recently Viewed | Visit product pages → scroll down → see "Recently Viewed" section |

### ServiceBridge Features

| Feature | How to verify |
|---------|--------------|
| Activity Page | Navigate to Services → Activity → see delivery log |
| Service Cards | Services Hub shows all 8 services with health indicators |
| Product Panel | Product detail → "Connected Services" shows 6-service grid |
| Order Panel | Order detail → "Service Notifications" shows FlowSend/SpyDrop status |
| Manual Dispatch | POST to `/api/v1/bridge/dispatch` → verify delivery recorded |

---
*See also: [Testing](TESTING.md) · [API Reference](API_REFERENCE.md) · [Setup](SETUP.md)*
