# Dropshipping Platform -- Phase 3 Feature Documentation

This document covers four major features introduced in Phase 3 of the dropshipping platform. Each feature is documented for four audiences: **Developer**, **Project Manager**, **QA Engineer**, and **End User**.

---

## Table of Contents

1. [Feature 1: Store Cloning](#feature-1-store-cloning)
2. [Feature 4: Normal Ecommerce Mode](#feature-4-normal-ecommerce-mode)
3. [Feature 6: DNS Management](#feature-6-dns-management)
4. [Feature 7: Domain Purchasing](#feature-7-domain-purchasing)

---

## Feature 1: Store Cloning

### Developer

#### Architecture

Store cloning is implemented as a single transactional operation that deep-copies a store and all its child entities. The clone service lives at `dropshipping/backend/app/services/clone_service.py`.

**Entry point:** `clone_store(db, user_id, source_store_id, new_name=None) -> Store`

The function performs cloning in a specific order because later steps depend on ID mappings produced by earlier steps:

1. Clone categories (returns `category_id_map`)
2. Clone products and variants (returns `product_id_map`, `variant_id_map`)
3. Clone suppliers (returns `supplier_id_map`)
4. Clone product-category junctions (using product and category ID maps)
5. Clone product-supplier junctions (using product and supplier ID maps)
6. Clone themes
7. Clone discounts and discount-product/discount-category junctions
8. Clone tax rules

Each `_clone_*` helper generates fresh UUIDs for every cloned record and returns an `old_id -> new_id` mapping dict. Junction tables (ProductCategory, ProductSupplier, DiscountProduct, DiscountCategory) are re-linked using these maps.

**Slug generation:** The cloned store's slug is produced by `generate_unique_slug(db, Store, clone_name)`, which generates slugs in the pattern `{original}-copy`, `{original}-copy-2`, `{original}-copy-3`, etc.

**Category hierarchy:** Categories are cloned in two passes. The first pass creates all categories without parent links. The second pass sets `parent_id` using the ID map to preserve the parent-child tree.

**Archived products:** Products with `status == "archived"` are excluded from cloning.

**Discounts:** Non-expired discounts are cloned. The `code` field is suffixed with `-copy` to avoid cross-store confusion. `times_used` is reset to `0`. Discounts whose `expires_at` is in the past are skipped even if their status has not been updated to `expired`.

#### API Contract

```
POST /api/v1/stores/{store_id}/clone
```

**Authentication:** Bearer token required. The `check_store_limit` dependency also verifies the user has not exceeded their plan's store limit.

**Request body** (`CloneStoreRequest`):

```json
{
  "new_name": "My Cloned Store"    // optional, defaults to "{original_name} (Copy)"
}
```

**Response** (201 Created, `CloneStoreResponse`):

```json
{
  "store": {
    "id": "uuid",
    "user_id": "uuid",
    "name": "My Cloned Store",
    "slug": "my-cloned-store",
    "niche": "electronics",
    "description": "...",
    "store_type": "dropshipping",
    "status": "active",
    "created_at": "2026-01-15T12:00:00Z",
    "updated_at": "2026-01-15T12:00:00Z"
  },
  "source_store_id": "uuid-of-original-store"
}
```

**Error responses:**
- `404` -- Source store not found or not owned by the user.
- `403` -- Store limit reached for the user's plan.

#### Key Files

| File | Purpose |
|------|---------|
| `backend/app/services/clone_service.py` | Core clone logic with all `_clone_*` helpers |
| `backend/app/api/stores.py` | `POST /{store_id}/clone` endpoint |
| `backend/app/schemas/store.py` | `CloneStoreRequest`, `CloneStoreResponse` |
| `backend/app/utils/slug.py` | `generate_unique_slug()` |
| `backend/tests/test_clone.py` | Backend unit/integration tests |
| `e2e/tests/dashboard/store-cloning.spec.ts` | End-to-end Playwright tests |

---

### Project Manager

#### Scope

Store Cloning allows merchants to duplicate an entire store configuration in one click. This is critical for merchants who run multiple stores with similar product catalogs or who want to test changes on a copy before applying them to a live store.

#### What Gets Cloned

| Entity | Cloned? | Notes |
|--------|---------|-------|
| Store settings (name, niche, description, currency, theme, logos, CSS) | Yes | Name defaults to "{original} (Copy)" |
| Products (non-archived) | Yes | Review counts and ratings reset |
| Product variants | Yes | All variant fields copied |
| Categories (with hierarchy) | Yes | Parent-child relationships preserved |
| Suppliers | Yes | All supplier metadata copied |
| Themes | Yes | Active/inactive state preserved |
| Discounts (non-expired) | Yes | Codes suffixed with `-copy`, usage reset to 0 |
| Tax rules (active) | Yes | All rate details copied |
| Orders | No | -- |
| Customers | No | -- |
| Reviews | No | -- |
| Analytics | No | -- |
| Webhooks | No | -- |
| Teams | No | -- |

#### Dependencies

- Plan-based store limits must be enforced (the clone counts as a new store).
- `generate_unique_slug()` utility must handle collision-free slug creation.

#### Milestones

- Backend service and tests: Complete
- API endpoint: Complete
- E2E tests: Complete
- Dashboard UI: Clone button on store settings page

---

### QA Engineer

#### Test Plan

**Backend tests** (`backend/tests/test_clone.py`):

1. **Basic clone** -- Clone a store with products, variants, categories, themes, discounts, tax rules, and suppliers. Verify all entities are duplicated with new UUIDs.
2. **Name override** -- Pass `new_name` and verify the cloned store uses it.
3. **Default name** -- Omit `new_name` and verify the clone is named `{original} (Copy)`.
4. **Slug uniqueness** -- Clone the same store twice. First clone gets `{slug}-copy`, second gets `{slug}-copy-2`.
5. **Discount code suffix** -- Verify cloned discount codes end with `-copy`.
6. **Discount usage reset** -- Verify `times_used` is `0` on all cloned discounts.
7. **Expired discounts excluded** -- Discounts with `expires_at` in the past are not cloned.
8. **Archived products excluded** -- Products with `status == "archived"` are not cloned.
9. **Category hierarchy** -- Clone a store with nested categories (parent/child). Verify parent-child relationships are preserved in the clone.
10. **Active theme preserved** -- The `is_active` flag on themes is copied correctly.
11. **Store ownership** -- Attempting to clone another user's store returns 404.
12. **Deleted store** -- Attempting to clone a soft-deleted store returns 404.
13. **Plan store limit** -- Attempting to clone when at the plan's store limit returns 403.

**E2E tests** (`e2e/tests/dashboard/store-cloning.spec.ts`):

14. Navigate to store settings, click "Clone Store", verify new store appears in the store list.
15. Verify cloned store has the same products, themes, and discounts.

#### Edge Cases

- Cloning a store with zero products (should succeed with empty product list).
- Cloning a store with discounts that reference products or categories (junction tables must be re-linked).
- Cloning a store with a supplier linked to multiple products.
- Concurrent clone requests for the same store (slug uniqueness must hold).

#### Acceptance Criteria

- Cloned store is fully independent -- modifying the clone does not affect the original.
- All IDs are new UUIDs (no shared references between source and clone).
- Response includes both the new store data and the `source_store_id`.
- The operation completes in a single database transaction.

---

### End User

#### What Is Store Cloning?

Store Cloning lets you create an exact copy of one of your existing stores. The copy includes all your products, themes, discounts, categories, tax rules, and supplier connections. Orders, customer data, and analytics are not copied -- the clone starts fresh.

#### How to Clone a Store

1. Open your **Dashboard** and navigate to the store you want to clone.
2. Go to **Store Settings**.
3. Click the **Clone Store** button.
4. Optionally, enter a new name for the cloned store. If you leave it blank, the clone will be named `{your store name} (Copy)`.
5. Click **Confirm**. The new store will appear in your store list within seconds.

#### What to Expect After Cloning

- The cloned store is immediately **active** and ready to configure.
- All product listings, pricing, and variants are copied over.
- Discount codes are modified slightly (suffixed with `-copy`) so they do not conflict with the original store's codes. Usage counters start at zero.
- Your active theme is carried over, so the clone looks identical to the original.
- No customer data or order history is copied -- the clone is a clean slate for new business.

#### Limits

- Cloning counts as creating a new store. If you have reached your plan's store limit, you will need to upgrade before cloning.

---

## Feature 4: Normal Ecommerce Mode

### Developer

#### Architecture

The `StoreType` enum on the `Store` model determines which features are available:

| Value | Description |
|-------|-------------|
| `dropshipping` | Products sourced from suppliers. No inventory management. |
| `ecommerce` | Own inventory, warehouses, fulfillment. Full inventory tracking. |
| `hybrid` | Mix of dropshipping and own-inventory products. |

**New models** in `backend/app/models/inventory.py`:

- **`Warehouse`** -- A physical fulfillment location. Fields: `id`, `store_id`, `name`, `address`, `city`, `state`, `country`, `zip_code`, `is_default`, `is_active`, `created_at`, `updated_at`.
- **`InventoryLevel`** -- Stock level for a variant at a warehouse. Unique constraint on `(variant_id, warehouse_id)`. Computed properties: `available_quantity` (`quantity - reserved_quantity`), `is_low_stock` (`available_quantity <= reorder_point`).
- **`InventoryAdjustment`** -- Immutable audit trail record for every stock change. Fields: `inventory_level_id`, `quantity_change` (signed delta), `reason` (enum), `reference_id`, `notes`, `created_at`.

**`AdjustmentReason` enum:** `received`, `sold`, `returned`, `damaged`, `correction`, `reserved`, `unreserved`, `transfer`.

**ProductVariant additions:** `barcode`, `weight`, `weight_unit`, `track_inventory`, `allow_backorder`.

**Inventory service** (`backend/app/services/inventory_service.py`):

| Function | Purpose |
|----------|---------|
| `create_warehouse()` | Create warehouse, unset previous default if needed |
| `list_warehouses()` | List all warehouses for a store |
| `get_warehouse()` | Get single warehouse with store ownership check |
| `update_warehouse()` | Partial update, handles default flag switching |
| `delete_warehouse()` | Delete non-default warehouse (400 if default) |
| `create_default_warehouse()` | Auto-create "Main Warehouse" for new ecommerce stores |
| `set_inventory_level()` | Create or update inventory level, generates adjustment record |
| `adjust_inventory()` | Apply signed delta, rejects negative result |
| `reserve_stock()` | Increment `reserved_quantity` for order lifecycle |
| `release_stock()` | Decrement `reserved_quantity` (order cancelled) |
| `fulfill_stock()` | Decrement both `quantity` and `reserved_quantity` (order shipped) |
| `get_low_stock_items()` | Items at or below reorder point |
| `get_inventory_summary()` | Aggregated stats: warehouses, total stock, reserved, low-stock count |

#### API Contract

All inventory endpoints are scoped under `/api/v1/stores/{store_id}/`. Authentication is required via Bearer token. Store ownership is verified on every request.

**Warehouse CRUD:**

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `POST` | `/stores/{store_id}/warehouses` | 201 | Create warehouse |
| `GET` | `/stores/{store_id}/warehouses` | 200 | List warehouses |
| `GET` | `/stores/{store_id}/warehouses/{warehouse_id}` | 200 | Get warehouse |
| `PATCH` | `/stores/{store_id}/warehouses/{warehouse_id}` | 200 | Update warehouse |
| `DELETE` | `/stores/{store_id}/warehouses/{warehouse_id}` | 204 | Delete warehouse |

**Create warehouse request:**

```json
{
  "name": "East Coast Warehouse",
  "address": "123 Main St",
  "city": "New York",
  "state": "NY",
  "country": "US",
  "zip_code": "10001",
  "is_default": false
}
```

**Inventory Management:**

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `POST` | `/stores/{store_id}/inventory` | 201 | Set inventory level |
| `GET` | `/stores/{store_id}/inventory` | 200 | List inventory levels (optional `?warehouse_id=`) |
| `POST` | `/stores/{store_id}/inventory/{id}/adjust` | 200 | Apply adjustment |
| `GET` | `/stores/{store_id}/inventory/{id}/adjustments` | 200 | List adjustment history |
| `GET` | `/stores/{store_id}/inventory/summary` | 200 | Aggregated stats |
| `GET` | `/stores/{store_id}/inventory/low-stock` | 200 | Low-stock alerts |

**Set inventory request:**

```json
{
  "variant_id": "uuid",
  "warehouse_id": "uuid",
  "quantity": 100,
  "reorder_point": 10,
  "reorder_quantity": 50
}
```

**Adjust inventory request:**

```json
{
  "quantity_change": -5,
  "reason": "damaged",
  "reference_id": null,
  "notes": "Dropped during unloading"
}
```

**Inventory summary response:**

```json
{
  "total_warehouses": 2,
  "total_variants_tracked": 45,
  "total_in_stock": 1200,
  "total_reserved": 80,
  "low_stock_count": 3
}
```

#### Key Files

| File | Purpose |
|------|---------|
| `backend/app/models/inventory.py` | Warehouse, InventoryLevel, InventoryAdjustment models |
| `backend/app/models/store.py` | StoreType enum |
| `backend/app/services/inventory_service.py` | All inventory business logic |
| `backend/app/api/inventory.py` | REST API endpoints |
| `backend/app/schemas/inventory.py` | Request/response Pydantic schemas |
| `backend/tests/test_inventory.py` | 45 backend tests |
| `e2e/tests/dashboard/inventory.spec.ts` | 10 E2E tests |

---

### Project Manager

#### Scope

Normal Ecommerce Mode transforms the platform from a dropshipping-only tool into a full ecommerce platform. Merchants can manage their own inventory across multiple warehouses, track stock levels in real time, and receive low-stock alerts.

#### Key Capabilities

- **Store type selection:** Merchants choose `dropshipping`, `ecommerce`, or `hybrid` when creating a store.
- **Multi-warehouse support:** Unlimited warehouses per store with one designated as default.
- **Inventory tracking:** Per-variant, per-warehouse stock levels with available/reserved breakdown.
- **Audit trail:** Every stock change is recorded as an immutable adjustment with reason, timestamp, and optional reference.
- **Stock reservation lifecycle:** Reserve on order creation, fulfill on shipment, release on cancellation.
- **Low-stock alerts:** Configurable reorder points per variant per warehouse.
- **Dashboard integration:** Inventory and Warehouses pages appear conditionally in the navigation only for ecommerce and hybrid stores.

#### Dependencies

- Store model must support the `store_type` enum.
- Default warehouse must be auto-created when a store is created with type `ecommerce` or `hybrid`.
- Dashboard navigation must conditionally render inventory pages based on store type.

#### Milestones

- Database models and migrations: Complete
- Inventory service with full CRUD and reservation lifecycle: Complete
- API endpoints (11 endpoints): Complete
- Backend tests (45 tests): Complete
- Dashboard UI (inventory page, warehouses page): Complete
- E2E tests (10 tests): Complete

---

### QA Engineer

#### Test Plan

**Backend tests** (`backend/tests/test_inventory.py` -- 45 tests):

**Warehouse CRUD:**
1. Create a warehouse with all fields. Verify response matches input.
2. Create a warehouse with `is_default=true`. Verify the previous default is unset.
3. List warehouses. Verify default warehouse appears first.
4. Update a warehouse name, address, and country.
5. Set a non-default warehouse as default. Verify old default loses the flag.
6. Delete a non-default warehouse. Verify 204 and it disappears from the list.
7. Attempt to delete the default warehouse. Verify 400 error.
8. Verify store ownership -- accessing another user's warehouse returns 404.

**Inventory Levels:**
9. Set inventory for a variant at a warehouse. Verify level is created with correct quantities.
10. Set inventory for the same variant/warehouse again. Verify it updates (not duplicates).
11. Verify the unique constraint on `(variant_id, warehouse_id)`.
12. List inventory levels for a store. Verify all levels returned.
13. Filter inventory levels by `warehouse_id`.
14. Verify `available_quantity = quantity - reserved_quantity`.

**Adjustments:**
15. Adjust inventory up (+10, reason: `received`). Verify new quantity.
16. Adjust inventory down (-5, reason: `damaged`). Verify new quantity.
17. Attempt to adjust below zero. Verify 400 error with descriptive message.
18. List adjustment history. Verify records are ordered newest first.
19. Verify adjustment includes `quantity_change`, `reason`, `notes`, `reference_id`, `created_at`.

**Stock Reservation Lifecycle:**
20. Reserve stock for an order. Verify `reserved_quantity` increments, `quantity` unchanged.
21. Attempt to reserve more than available. Verify error.
22. Fulfill reserved stock. Verify both `quantity` and `reserved_quantity` decrement.
23. Release reserved stock (order cancelled). Verify `reserved_quantity` decrements, `quantity` unchanged.

**Summary and Alerts:**
24. Get inventory summary. Verify aggregated totals match individual levels.
25. Set reorder point. Stock below threshold appears in low-stock list.
26. Stock above threshold does not appear in low-stock list.

**E2E tests** (`e2e/tests/dashboard/inventory.spec.ts` -- 10 tests):
27. Create ecommerce store, verify default warehouse exists.
28. Add warehouse through dashboard UI.
29. Set inventory levels through the inventory page.
30. Verify low-stock badge appears when stock drops below reorder point.

#### Edge Cases

- Warehouse with no inventory levels (valid, should list with zero stock).
- Setting inventory level with `quantity=0` (valid, creates the tracking record).
- Concurrent adjustments to the same inventory level (database-level integrity).
- Creating a dropshipping store and verifying inventory pages are hidden.
- Fulfilling more than reserved quantity (should fail).

#### Acceptance Criteria

- Ecommerce stores get a default "Main Warehouse" automatically on creation.
- Inventory pages are visible only for `ecommerce` and `hybrid` store types.
- Every quantity change produces an audit trail record.
- `available_quantity` never goes negative (enforced by `max(0, quantity - reserved_quantity)`).
- Deleting a default warehouse is rejected with a clear error message.

---

### End User

#### What Is Ecommerce Mode?

When you create a store, you can choose one of three modes:

- **Dropshipping** -- You list products from suppliers who ship directly to your customers. No inventory to manage.
- **Ecommerce** -- You own and warehouse your products. Full inventory management is available.
- **Hybrid** -- A mix of both. Some products come from suppliers, others from your own stock.

If you choose **Ecommerce** or **Hybrid**, you get access to the Inventory and Warehouses sections in your dashboard.

#### Managing Warehouses

1. Go to **Dashboard > Warehouses**.
2. Your store starts with a **Main Warehouse** (created automatically).
3. Click **Add Warehouse** to add more locations. Enter the warehouse name, address, city, state, country, and ZIP code.
4. Mark one warehouse as the **default** -- new inventory entries will default to this location.
5. You can edit or delete warehouses at any time (except the default warehouse -- reassign the default first).

#### Tracking Inventory

1. Go to **Dashboard > Inventory**.
2. For each product variant, set the stock quantity at each warehouse.
3. Set a **reorder point** -- when available stock drops to this number, you will see a low-stock alert.
4. Set a **reorder quantity** -- the suggested amount to order from your supplier.

#### Understanding Stock Numbers

- **Quantity** -- Total units physically in the warehouse.
- **Reserved** -- Units held for pending orders that have not shipped yet.
- **Available** -- Units that can be sold (`Quantity - Reserved`).

#### Adjustment History

Every change to your stock is recorded automatically:
- Stock received from a supplier
- Units sold (shipped)
- Customer returns
- Damaged goods removed
- Manual corrections
- Transfers between warehouses

Go to a product's inventory detail page and click **View History** to see the full audit trail.

#### Low-Stock Alerts

The **Inventory Summary** on your dashboard shows:
- Total warehouses
- Total units in stock
- Total units reserved for orders
- Number of items at or below the reorder point

Items flagged as low-stock appear in the **Low Stock** section for quick action.

---

## Feature 6: DNS Management

### Developer

#### Architecture

DNS management uses a provider abstraction pattern with four implementations:

```
AbstractDnsProvider (base.py)
    |-- CloudflareDnsProvider (cloudflare.py)
    |-- Route53DnsProvider (route53.py)
    |-- GoogleCloudDnsProvider (google_dns.py)
    |-- MockDnsProvider (mock.py)
```

**Factory:** `get_dns_provider()` in `app/services/dns/factory.py` reads `settings.dns_provider_mode` (defaults to `"mock"`) and returns the appropriate provider instance. Unknown modes fall back to `MockDnsProvider`.

**Provider interface** (6 abstract methods):

| Method | Purpose |
|--------|---------|
| `create_record(zone_id, record)` | Create a DNS record in a zone |
| `list_records(zone_id)` | List all records in a zone |
| `update_record(zone_id, record_id, record)` | Update an existing record |
| `delete_record(zone_id, record_id)` | Delete a record |
| `get_zone_id(domain)` | Resolve domain to zone ID |
| `verify_propagation(domain, type, value)` | Check if a record has propagated |

**Service layer:** `dns_management_service.py` coordinates between the provider abstraction and the database:

| Function | Behavior |
|----------|----------|
| `auto_configure_dns(db, domain_id)` | Creates A record (`@` -> platform IP) and CNAME record (`www` -> platform hostname). Updates `CustomDomain` with `dns_provider`, `dns_zone_id`, `auto_dns_configured=True`. |
| `provision_ssl(db, domain_id)` | Sets `ssl_provisioned=True`, generates `ssl_certificate_id`, sets `ssl_provider="letsencrypt"`, `ssl_expires_at` = now + 90 days, status = `active`. |
| `verify_dns_propagation(db, domain_id)` | Checks all managed records via provider. Returns `{propagated, total_records, verified_records, details}`. |
| `create_dns_record(...)` | Creates record in both provider and database. `is_managed=False` for manual records. |
| `update_dns_record(...)` | Updates record in both provider and database. Partial update (only non-None fields). |
| `delete_dns_record(...)` | Deletes from both provider and database. |
| `get_dns_status(db, domain_id)` | Returns `{domain, dns_configured, ssl_provisioned, records_count, propagation_status}`. |

**Models:** `DnsRecordEntry` in `app/models/domain.py` with fields: `domain_id`, `record_type` (A, AAAA, CNAME, MX, TXT, NS, SRV, CAA), `name`, `value`, `ttl`, `priority`, `provider_record_id`, `is_managed`.

#### API Contract

All DNS endpoints are nested under `/api/v1/stores/{store_id}/domain/`. Authentication is required via Bearer token. Store ownership is verified on every request.

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `POST` | `/stores/{s}/domain/dns/auto-configure` | 200 | Auto-create A + CNAME records |
| `GET` | `/stores/{s}/domain/dns/records` | 200 | List all DNS records |
| `POST` | `/stores/{s}/domain/dns/records` | 201 | Create a manual DNS record |
| `PATCH` | `/stores/{s}/domain/dns/records/{r}` | 200 | Update a DNS record |
| `DELETE` | `/stores/{s}/domain/dns/records/{r}` | 204 | Delete a DNS record |
| `POST` | `/stores/{s}/domain/ssl/provision` | 200 | Provision SSL certificate |
| `GET` | `/stores/{s}/domain/dns/status` | 200 | Get DNS status summary |

**Auto-configure response:**

```json
{
  "records_created": 2,
  "records": [
    {
      "id": "uuid",
      "domain_id": "uuid",
      "record_type": "A",
      "name": "@",
      "value": "192.0.2.1",
      "ttl": 3600,
      "priority": null,
      "provider_record_id": "mock-...",
      "is_managed": true,
      "created_at": "...",
      "updated_at": "..."
    },
    {
      "id": "uuid",
      "domain_id": "uuid",
      "record_type": "CNAME",
      "name": "www",
      "value": "proxy.platform.app",
      "ttl": 3600,
      "priority": null,
      "provider_record_id": "mock-...",
      "is_managed": true,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

**Create DNS record request:**

```json
{
  "record_type": "MX",
  "name": "mail",
  "value": "mail.example.com",
  "ttl": 3600,
  "priority": 10
}
```

**SSL provision response:**

```json
{
  "ssl_provisioned": true,
  "ssl_certificate_id": "ssl-cert-a1b2c3d4e5f6",
  "ssl_expires_at": "2026-05-15T12:00:00Z"
}
```

**DNS status response:**

```json
{
  "domain": "mystore.com",
  "dns_configured": true,
  "ssl_provisioned": true,
  "records_count": 3,
  "propagation_status": "propagated"
}
```

#### Key Files

| File | Purpose |
|------|---------|
| `backend/app/services/dns/base.py` | `AbstractDnsProvider`, `DnsRecord` dataclass |
| `backend/app/services/dns/factory.py` | `get_dns_provider()` factory |
| `backend/app/services/dns/cloudflare.py` | Cloudflare implementation |
| `backend/app/services/dns/route53.py` | AWS Route53 implementation |
| `backend/app/services/dns/google_dns.py` | Google Cloud DNS implementation |
| `backend/app/services/dns/mock.py` | Mock implementation for dev/test |
| `backend/app/services/dns_management_service.py` | High-level DNS business logic |
| `backend/app/api/dns.py` | REST API endpoints (7 routes) |
| `backend/app/schemas/dns.py` | Request/response Pydantic schemas |
| `backend/app/models/domain.py` | `DnsRecordEntry`, `CustomDomain` DNS fields |
| `backend/tests/test_dns_management.py` | 34 backend tests |

#### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `dns_provider_mode` | `"mock"` | Provider: `mock`, `cloudflare`, `route53`, `google` |
| `cloudflare_api_token` | `""` | Cloudflare API token |
| `route53_access_key_id` | `""` | AWS access key |
| `route53_secret_access_key` | `""` | AWS secret key |
| `route53_region` | `"us-east-1"` | AWS region |
| `google_dns_project_id` | `""` | GCP project ID |
| `google_dns_credentials_json` | `""` | GCP credentials |
| `platform_ip_address` | `"192.0.2.1"` | Platform IP for A records |
| `platform_cname_target` | `"proxy.platform.app"` | Platform hostname for CNAME records |

---

### Project Manager

#### Scope

DNS Management automates the configuration of DNS records when merchants connect custom domains to their stores. It also provides a manual DNS record editor for advanced users who need to configure email routing (MX), domain verification (TXT), or other custom records.

#### Key Capabilities

- **Auto-configuration:** One-click setup of A and CNAME records for custom domains.
- **Manual record management:** Full CRUD for any DNS record type (A, AAAA, CNAME, MX, TXT, NS, SRV, CAA).
- **SSL provisioning:** Automatic SSL certificate issuance (Let's Encrypt) after DNS is configured.
- **Propagation monitoring:** Real-time check of whether DNS records have propagated globally.
- **Multi-provider support:** Cloudflare, Route53, Google Cloud DNS, with mock for development.

#### Dependencies

- Custom domain must already be configured for the store.
- Provider credentials must be set in environment/config for production use.
- SSL provisioning depends on successful DNS configuration.

#### Milestones

- Provider abstraction layer (4 providers): Complete
- DNS management service: Complete
- API endpoints (7 endpoints): Complete
- Backend tests (34 tests): Complete
- Dashboard UI integration: Complete

---

### QA Engineer

#### Test Plan

**Backend tests** (`backend/tests/test_dns_management.py` -- 34 tests):

**Auto-configuration:**
1. Auto-configure a domain. Verify exactly 2 records created (A + CNAME).
2. Verify A record: `name="@"`, `value=platform_ip`, `ttl=3600`, `is_managed=True`.
3. Verify CNAME record: `name="www"`, `value=platform_cname`, `ttl=3600`, `is_managed=True`.
4. Verify `CustomDomain.auto_dns_configured` is set to `True`.
5. Verify `CustomDomain.dns_provider` matches the configured mode.
6. Auto-configure for a non-existent domain ID. Verify `ValueError`.

**SSL Provisioning:**
7. Provision SSL. Verify `ssl_provisioned=True`.
8. Verify `ssl_certificate_id` is populated (format: `ssl-cert-{12-hex}`).
9. Verify `ssl_provider` is `"letsencrypt"`.
10. Verify `ssl_expires_at` is approximately 90 days in the future.
11. Verify domain status is set to `active`.
12. Provision SSL for non-existent domain. Verify `ValueError`.

**DNS Records CRUD:**
13. Create a manual DNS record. Verify response includes all fields.
14. Verify manual records have `is_managed=False`.
15. List DNS records. Verify both managed and manual records appear.
16. Update a record's value and TTL. Verify changes persist.
17. Delete a record. Verify it disappears from the list.
18. Delete a non-existent record. Verify `ValueError`.

**Propagation:**
19. Verify propagation for a domain with all records propagated. Result: `propagated=True`.
20. Verify propagation for a domain with no records. Result: `propagated=False, total_records=0`.

**API-level:**
21. All endpoints return 401 without authentication.
22. All endpoints return 404 for a store not owned by the user.
23. All endpoints return 404 for a store with no custom domain.
24. TTL validation: reject values below 60 or above 86400.

#### Edge Cases

- Auto-configuring a domain that already has managed records (should create additional records or handle idempotently).
- Updating a managed record (allowed but may break auto-configuration).
- Deleting a managed record (allowed, triggers warning log).
- Provider returns an error during record creation (should propagate as HTTP error).

#### Acceptance Criteria

- Auto-configure creates exactly 2 records (A + CNAME) with correct values.
- SSL provisioning sets all certificate fields on the `CustomDomain`.
- Manual and managed records coexist in the same record list.
- Propagation status correctly reflects the state of all managed records.
- Record CRUD operations update both the database and the DNS provider.

---

### End User

#### What Is DNS Management?

DNS (Domain Name System) records tell the internet where to find your store when someone types your domain name. When you connect a custom domain to your store, the platform needs to set up these records correctly.

#### Auto-Configuration (Recommended)

For most merchants, auto-configuration is the simplest option:

1. Go to **Dashboard > Settings > Custom Domain**.
2. Enter your domain name and verify ownership.
3. Click **Auto-Configure DNS**. The platform will create the necessary records automatically:
   - An **A record** pointing your root domain (e.g., `mystore.com`) to the platform.
   - A **CNAME record** pointing `www.mystore.com` to the platform.
4. Click **Provision SSL** to get a free SSL certificate for your domain.
5. Wait a few minutes for DNS changes to propagate. Use the **Check Status** button to verify.

#### Manual DNS Record Management

If you need more control (for example, to set up email routing or domain verification):

1. Go to **Dashboard > Settings > Custom Domain > DNS Records**.
2. Click **Add Record**.
3. Choose the record type (A, AAAA, CNAME, MX, TXT, NS, SRV, or CAA).
4. Enter the record name (e.g., `@` for root, `mail` for a subdomain), value, and TTL.
5. For MX records (email), set the priority value.
6. Click **Save**. The record will be created at your DNS provider.

You can also edit or delete records from this page.

#### DNS Status

The DNS status panel shows:
- Whether DNS has been auto-configured.
- Whether SSL is provisioned.
- The total number of DNS records.
- Whether all records have propagated globally.

Propagation typically takes 5-30 minutes, but can take up to 48 hours in rare cases.

---

## Feature 7: Domain Purchasing

### Developer

#### Architecture

Domain purchasing uses a registrar abstraction pattern with three implementations:

```
AbstractDomainProvider (base.py)
    |-- ResellerClubProvider (resellerclub.py)
    |-- SquarespaceDomainProvider (squarespace.py)
    |-- MockDomainProvider (mock.py)
```

**Factory:** `get_domain_provider()` in `app/services/domain_registrar/factory.py` reads `settings.domain_provider_mode` (defaults to `"mock"`) and returns the appropriate provider instance.

**Provider interface** (6 abstract methods):

| Method | Purpose |
|--------|---------|
| `search_domains(query, tlds)` | Search available domains across TLDs |
| `purchase_domain(domain, years, contact_info)` | Purchase a domain |
| `check_availability(domain)` | Check single domain availability |
| `renew_domain(domain, years)` | Renew registration |
| `set_nameservers(domain, nameservers)` | Set nameservers |
| `get_domain_info(domain)` | Get domain details |

**Service layer:** `domain_purchase_service.py` orchestrates the full purchase flow:

1. `search_available_domains(query, tlds)` -- Searches registrar, returns availability and pricing per TLD.
2. `purchase_domain(db, store_id, user_id, domain, years, contact_info)` -- Full purchase lifecycle:
   - Verify store ownership
   - Check store does not already have a custom domain
   - Check domain is not used by another store
   - Purchase via registrar provider
   - Create `CustomDomain` record with `is_purchased=True`, `purchase_provider`, `purchase_date`, `expiry_date`, `registrar_order_id`
   - Set nameservers to platform
   - Auto-configure DNS (non-blocking -- failure does not block purchase)
   - Provision SSL (non-blocking -- failure does not block purchase)
3. `renew_domain(db, domain_id, years)` -- Renews via registrar, updates `expiry_date` and `registrar_order_id`.
4. `list_owned_domains(db, user_id)` -- Lists all purchased domains across user's stores.
5. `toggle_auto_renew(db, domain_id, auto_renew)` -- Flips `auto_renew` flag.

**CustomDomain purchase fields:**

| Field | Type | Description |
|-------|------|-------------|
| `purchase_provider` | `String` | Registrar used (e.g., `"mock"`, `"resellerclub"`) |
| `purchase_date` | `DateTime` | When domain was purchased |
| `expiry_date` | `DateTime` | When domain expires |
| `auto_renew` | `Boolean` | Auto-renewal toggle |
| `registrar_order_id` | `String` | Registrar's order identifier |
| `is_purchased` | `Boolean` | Whether purchased via platform |

#### API Contract

Domain search and owned domains are **user-scoped** (no store_id). Purchase, renewal, and auto-renew are **store-scoped**.

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `GET` | `/api/v1/domains/search?q={query}&tlds={tlds}` | 200 | Search available domains |
| `GET` | `/api/v1/domains/owned` | 200 | List user's purchased domains |
| `POST` | `/api/v1/stores/{s}/domain/purchase` | 201 | Purchase domain for store |
| `POST` | `/api/v1/stores/{s}/domain/renew` | 200 | Renew domain registration |
| `PATCH` | `/api/v1/stores/{s}/domain/auto-renew` | 200 | Toggle auto-renewal |

**Search request:**

```
GET /api/v1/domains/search?q=mystore&tlds=com,io,store
```

**Search response:**

```json
{
  "results": [
    {
      "domain": "mystore.com",
      "available": true,
      "price": "12.99",
      "currency": "USD",
      "period_years": 1
    },
    {
      "domain": "mystore.io",
      "available": false,
      "price": "39.99",
      "currency": "USD",
      "period_years": 1
    },
    {
      "domain": "mystore.store",
      "available": true,
      "price": "24.99",
      "currency": "USD",
      "period_years": 1
    }
  ]
}
```

**Purchase request:**

```json
{
  "domain": "mystore.com",
  "years": 1,
  "contact_info": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "address": "123 Main St",
    "city": "New York",
    "state": "NY",
    "country": "US",
    "zip_code": "10001"
  }
}
```

**Purchase response** (201 Created):

```json
{
  "domain": "mystore.com",
  "order_id": "order-abc123",
  "status": "success",
  "expiry_date": "2027-02-14T12:00:00Z",
  "auto_dns_configured": true,
  "ssl_provisioned": true
}
```

**Renew request:**

```json
{
  "years": 1
}
```

**Renew response:**

```json
{
  "domain": "mystore.com",
  "new_expiry_date": "2028-02-14T12:00:00Z",
  "order_id": "renewal-def456"
}
```

**Auto-renew toggle request:**

```json
{
  "auto_renew": true
}
```

**Auto-renew toggle response:**

```json
{
  "domain": "mystore.com",
  "auto_renew": true
}
```

**Owned domains response:**

```json
{
  "domains": [
    {
      "id": "uuid",
      "store_id": "uuid",
      "domain": "mystore.com",
      "status": "active",
      "purchase_provider": "mock",
      "purchase_date": "2026-02-14T12:00:00Z",
      "expiry_date": "2027-02-14T12:00:00Z",
      "auto_renew": false,
      "is_purchased": true,
      "ssl_provisioned": true,
      "auto_dns_configured": true
    }
  ]
}
```

#### Key Files

| File | Purpose |
|------|---------|
| `backend/app/services/domain_registrar/base.py` | `AbstractDomainProvider`, data classes |
| `backend/app/services/domain_registrar/factory.py` | `get_domain_provider()` factory |
| `backend/app/services/domain_registrar/resellerclub.py` | ResellerClub implementation |
| `backend/app/services/domain_registrar/squarespace.py` | Squarespace implementation |
| `backend/app/services/domain_registrar/mock.py` | Mock implementation |
| `backend/app/services/domain_purchase_service.py` | High-level purchase/renew logic |
| `backend/app/api/domain_purchase.py` | REST API endpoints (5 routes) |
| `backend/app/schemas/domain_purchase.py` | Request/response Pydantic schemas |
| `backend/app/models/domain.py` | `CustomDomain` purchase fields |
| `backend/tests/test_domain_purchase.py` | 28 backend tests |

#### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `domain_provider_mode` | `"mock"` | Provider: `mock`, `resellerclub`, `squarespace` |
| `resellerclub_api_key` | `""` | ResellerClub API key |
| `resellerclub_reseller_id` | `""` | ResellerClub reseller ID |
| `squarespace_api_key` | `""` | Squarespace/Google Domains API key |
| `platform_nameservers` | `"ns1.platform.app,ns2.platform.app"` | Platform nameservers set after purchase |

---

### Project Manager

#### Scope

Domain Purchasing enables merchants to search for, register, and manage domain names directly from the platform dashboard -- eliminating the need to use a separate domain registrar. The platform handles the full lifecycle: search, purchase, DNS configuration, SSL provisioning, renewal, and auto-renewal.

#### Key Capabilities

- **Domain search:** Search across multiple TLDs (default: `.com`, `.io`, `.store`) with real-time availability and pricing.
- **One-click purchase:** Purchase a domain, and the platform automatically configures nameservers, DNS records, and SSL.
- **Domain portfolio:** View all purchased domains across stores in one place.
- **Renewal management:** Manually renew domains or enable auto-renewal.
- **Multi-registrar support:** ResellerClub, Squarespace (formerly Google Domains), with mock for development.

#### Dependencies

- Feature 6 (DNS Management) must be complete -- domain purchase triggers `auto_configure_dns()` and `provision_ssl()`.
- Registrar API credentials must be configured for production.
- Payment integration is needed for production domain purchases (currently using mock/test registrar).

#### Milestones

- Registrar abstraction layer (3 providers): Complete
- Domain purchase service with full lifecycle: Complete
- API endpoints (5 endpoints): Complete
- Backend tests (28 tests): Complete
- Dashboard UI (search, purchase, manage domains): Complete

---

### QA Engineer

#### Test Plan

**Backend tests** (`backend/tests/test_domain_purchase.py` -- 28 tests):

**Domain Search:**
1. Search for a domain. Verify results contain one entry per TLD.
2. Verify each result includes `domain`, `available`, `price`, `currency`, `period_years`.
3. Search with custom TLD list. Verify results match requested TLDs.
4. Search with empty query. Verify validation error.

**Domain Purchase:**
5. Purchase a domain for a store. Verify 201 response with `status="success"`.
6. Verify `CustomDomain` record created with `is_purchased=True`.
7. Verify `purchase_provider` matches configured mode.
8. Verify `purchase_date` is set to approximately now.
9. Verify `expiry_date` is set (based on registrar response).
10. Verify `registrar_order_id` is populated.
11. Verify DNS auto-configuration ran (A + CNAME records created).
12. Verify SSL was provisioned (`ssl_provisioned=True`).
13. Purchase for a store that already has a domain. Verify 400 error: "already has a custom domain".
14. Purchase a domain already used by another store. Verify 400 error: "already in use".
15. Purchase for another user's store. Verify 404 error.
16. Purchase for a deleted store. Verify 404 error.

**Domain Renewal:**
17. Renew a purchased domain. Verify new `expiry_date` is extended.
18. Verify `registrar_order_id` is updated.
19. Renew a domain not purchased via platform. Verify 400 error.
20. Renew for a non-existent domain. Verify 404 error.

**Auto-Renewal:**
21. Enable auto-renew. Verify `auto_renew=True` in response.
22. Disable auto-renew. Verify `auto_renew=False` in response.
23. Toggle auto-renew on a non-purchased domain. Verify 400 error.

**Owned Domains:**
24. List owned domains. Verify only `is_purchased=True` domains appear.
25. Verify domains from deleted stores are excluded.
26. Verify response includes all purchase metadata fields.

**API-level:**
27. All endpoints return 401 without authentication.
28. Verify `years` validation: must be 1-10.

#### Edge Cases

- DNS auto-configuration fails after purchase (should not block purchase -- `auto_dns_configured=false` in response).
- SSL provisioning fails after purchase (should not block purchase -- `ssl_provisioned=false` in response).
- Registrar returns `"pending"` status (should propagate as error since only `"success"` is accepted).
- Domain name with mixed case (should be normalized to lowercase).
- Domain name with leading/trailing whitespace (should be trimmed).
- Concurrent purchase of the same domain for different stores.

#### Acceptance Criteria

- The full purchase flow (buy + nameservers + DNS + SSL) completes successfully for the mock provider.
- Purchased domains appear in the "owned domains" list.
- Renewal extends the `expiry_date` correctly.
- Auto-renew toggle persists and is reflected in the domain response.
- DNS and SSL failures during purchase are non-blocking (domain is still created).
- Duplicate domain purchase is prevented with a clear error message.

---

### End User

#### What Is Domain Purchasing?

Domain Purchasing lets you search for and buy domain names directly from your dashboard. No need to go to a separate registrar like GoDaddy or Namecheap -- everything is handled within the platform.

#### How to Search for a Domain

1. Go to **Dashboard > Settings > Custom Domain**.
2. Click **Search for a Domain**.
3. Type the domain name you want (for example, `mystore`).
4. The platform will check availability across multiple extensions (`.com`, `.io`, `.store`).
5. Each result shows whether the domain is available and its price.

#### How to Purchase a Domain

1. From the search results, click **Buy** next to the available domain you want.
2. Choose the registration period (1 to 10 years).
3. Enter your contact information (required by domain registrars).
4. Click **Purchase**.
5. The platform will:
   - Register the domain in your name.
   - Point the domain to your store (DNS configuration).
   - Set up a free SSL certificate (HTTPS).
6. Within a few minutes, your store will be live at your new domain.

#### Managing Your Domains

**View all domains:** Go to **Dashboard > Domains** to see all domains you have purchased across all your stores.

**Renew a domain:**
1. Go to the store's **Custom Domain** settings.
2. Click **Renew** and choose the number of years.
3. The domain's expiry date will be extended.

**Auto-renewal:**
1. Go to the store's **Custom Domain** settings.
2. Toggle **Auto-Renew** on or off.
3. When enabled, the platform will automatically renew your domain before it expires.

#### What Happens After Purchase

| Step | Automatic? | What It Does |
|------|-----------|--------------|
| Domain registration | Yes | Registers the domain with the registrar |
| Nameserver configuration | Yes | Points domain to platform servers |
| DNS records (A + CNAME) | Yes | Routes traffic from your domain to your store |
| SSL certificate | Yes | Enables HTTPS for secure browsing |

All four steps happen automatically. If any step fails, the domain purchase itself is preserved -- you can retry DNS or SSL configuration later from the dashboard.

#### Domain Expiry

- Domains are registered for the period you choose (1-10 years).
- Your dashboard shows the expiry date for each domain.
- Enable auto-renewal to avoid losing your domain. Without auto-renewal, you must manually renew before the expiry date.
