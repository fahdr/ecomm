# SourcePilot -- End User Guide

## What is SourcePilot?

SourcePilot is a product import tool for dropshipping merchants. It helps you find products from supplier platforms like AliExpress, CJ Dropshipping, and Spocket, then import them directly into your online store. You can also monitor supplier prices to stay competitive.

### Key Capabilities

- **Search supplier catalogs** for products across multiple platforms
- **Preview product details** (price, images, variants, shipping) before importing
- **Import products** into your connected store with one click or in bulk
- **Monitor supplier prices** and get notified when they change
- **Manage multiple stores** with a default import target
- **Track import history** with full audit trail

---

## Getting Started

### 1. Create Your Account

1. Open the SourcePilot dashboard in your browser.
2. Click **Register** and enter your email address and a password (minimum 8 characters).
3. You will be logged in automatically after registration.
4. Your account starts on the **Free plan** (10 imports per month).

### 2. Connect Your Store

Before importing products, you need to connect at least one dropshipping store:

1. Go to **Connections** in the sidebar navigation.
2. Click **Connect Store**.
3. Enter your store details:
   - **Store Name**: A display name you choose (e.g., "My Shopify Store")
   - **Platform**: Select your e-commerce platform (Shopify, WooCommerce, etc.)
   - **Store URL**: Your store's web address
   - **API Key** (optional): If your platform requires it for integration
4. Click **Save**.

Your first store connection is automatically set as the **default import target**. When you have multiple stores connected, the default store receives imports unless you specify otherwise.

### 3. Connect Your Supplier Accounts (Optional)

For full supplier API access, connect your supplier platform accounts:

1. Go to **Suppliers** in the sidebar.
2. Click **Connect Account**.
3. Enter your supplier account details:
   - **Name**: A label for this account (e.g., "Main AliExpress Account")
   - **Platform**: AliExpress, CJ Dropshipping, or Spocket
   - **Credentials**: Your platform API key or credentials
4. Click **Save**.

You can connect multiple accounts per platform.

---

## Dashboard Overview

The **Dashboard** is your home page after logging in. It shows four KPI cards at a glance:

| Card | Description |
|---|---|
| **Imports This Month** | Number of products you have imported during the current billing month |
| **Active Price Watches** | Number of products you are monitoring for price changes |
| **Connected Stores** | Number of stores linked to your account |
| **Current Plan** | Your subscription tier and status |

Below the KPI cards, **Quick Action** buttons let you jump to the most common tasks:
- **New Import** -- Start importing a product
- **Search Products** -- Browse supplier catalogs
- **View History** -- See your import history
- **Price Watch** -- Monitor supplier prices
- **Manage Stores** -- View your connected stores

---

## Importing Products

### Single Import

1. Go to **Imports** in the sidebar.
2. Enter the **product URL** from the supplier platform (e.g., an AliExpress product link).
3. Select the **source** platform (AliExpress, CJ Dropshipping, Spocket, or Manual).
4. Optionally select a **target store** (defaults to your default store).
5. Optionally set **import configuration**:
   - Markup percentage
   - Product tags
   - Compare-at discount
6. Click **Import**.

The import job will appear in your import list with a **Pending** status. It will progress through:
- **Pending** -- Queued for processing
- **Running** -- Actively importing
- **Completed** -- Product successfully created in your store
- **Failed** -- An error occurred (you can retry)

### Bulk Import

Import multiple products at once:

1. Go to **Imports** in the sidebar.
2. Enter up to **50 product URLs** (one per line or comma-separated).
3. Select the source platform (all URLs must be from the same platform).
4. Click **Bulk Import**.

Each URL creates a separate import job that processes independently.

### Managing Imports

- **View Details**: Click any import to see its full status and product data.
- **Cancel**: Cancel a pending or running import by clicking the Cancel button.
- **Retry**: Retry a failed or cancelled import to restart processing.
- **Filter**: Use the status and store filters to narrow your import list.

---

## Searching Products

### Search Supplier Catalogs

1. Go to **Products** in the sidebar.
2. Enter a search term (e.g., "wireless earbuds", "yoga mat", "phone case").
3. Optionally select a specific supplier platform or search across all.
4. Browse the results with product images, prices, ratings, and order counts.
5. Click a product to **preview** its full details.

### Preview Before Import

1. Click **Preview** on any search result, or enter a product URL directly.
2. The preview shows:
   - Product title and description
   - Price and currency
   - Product images
   - Available variants (colors, sizes, etc.)
   - Supplier name and rating
   - Order count and popularity
   - Shipping cost and estimated delivery time
3. If the product looks good, click **Import** to add it to your store.

Previewed products are cached for 24 hours, so loading them again will be faster.

---

## Price Monitoring

### Adding a Price Watch

1. Go to **Price Watch** in the sidebar.
2. Click **Add Watch**.
3. Enter the **product URL** from the supplier platform.
4. Select the **source** platform.
5. Set the **threshold** (default 10%) -- you will be alerted when the price changes by more than this percentage.
6. Optionally link the watch to a specific **store connection**.
7. Click **Save**.

### Viewing Price Watches

Your price watch list shows:
- Product URL and source platform
- Last known price and current price
- Whether the price has changed (flagged with a visual indicator)
- Last check timestamp

### Syncing Prices

Prices are checked automatically on a regular schedule. You can also trigger an immediate check:

1. Go to **Price Watch** in the sidebar.
2. Click **Sync Now**.
3. The system checks all active watches and updates prices.
4. A summary shows how many products were checked and how many had price changes.

### Removing a Price Watch

Click the **Delete** button next to any watch to stop monitoring that product.

---

## Managing Store Connections

### Viewing Connections

Go to **Connections** to see all your connected stores. The **default** store is highlighted and listed first.

### Setting a Default Store

Your default store receives imports when you do not specify a target store:

1. Go to **Connections**.
2. Find the store you want as your default.
3. Click **Set as Default**.

Only one store can be the default at a time. Setting a new default automatically removes the default status from the previous one.

### Updating a Connection

Click **Edit** on any connection to update:
- Store name
- Store URL
- API key

### Disconnecting a Store

Click **Disconnect** to remove a store connection. If you disconnect the default store, the next oldest store is automatically promoted to default.

---

## Managing Supplier Accounts

### Viewing Accounts

Go to **Suppliers** to see all your connected supplier accounts, organized by platform.

### Updating an Account

Click **Edit** on any account to:
- Change the display name
- Update credentials (API keys)
- Toggle active/inactive status (inactive accounts are skipped during operations)

### Disconnecting an Account

Click **Disconnect** to permanently remove a supplier account and its stored credentials.

---

## Billing and Plans

### Viewing Plans

Go to **Billing** to see all available plans:

| Plan | Price | What You Get |
|---|---|---|
| **Free** | $0/month | 10 imports per month, 25 price watches, no API access |
| **Pro** | $29/month | 100 imports per month, 500 price watches, API key access, 14-day trial |
| **Enterprise** | $99/month | Unlimited imports, unlimited price watches, API key access, 14-day trial |

### Upgrading Your Plan

1. Go to **Billing**.
2. Click **Upgrade** on the plan you want.
3. You will be redirected to a secure checkout page.
4. Enter your payment details and confirm.
5. Your plan upgrades immediately -- new limits take effect right away.

### Managing Your Subscription

After subscribing, you can:
- **View your current plan and usage** on the Billing page
- **Manage your subscription** (update payment method, cancel) via the Stripe Customer Portal
- **See usage metrics** showing how many imports and price watches you have used this month

### What Happens When You Hit Your Limit

If you reach your plan's import limit for the month:
- Attempting to create a new import returns an error: "Import limit reached for your plan."
- Existing imports continue processing normally.
- Your limit resets at the start of the next billing month.
- You can **upgrade your plan** at any time to get more imports immediately.

---

## API Keys (For Developers)

If you are on the **Pro** or **Enterprise** plan, you can generate API keys for programmatic access:

### Creating an API Key

1. Go to **API Keys** (under Settings).
2. Click **Create Key**.
3. Enter a **name** for the key (e.g., "My Integration").
4. Select **scopes** (permissions the key grants, default is "read").
5. Click **Create**.
6. **Copy the key immediately** -- it is only shown once for security.

### Using an API Key

Include the key in the `X-API-Key` header of your API requests:

```
X-API-Key: so_live_your_key_here
```

### Revoking an API Key

If a key is compromised or no longer needed:
1. Go to **API Keys**.
2. Find the key by its prefix (first few characters are shown).
3. Click **Revoke**.

Revoked keys stop working immediately.

---

## Frequently Asked Questions

### Can I import from any supplier?

SourcePilot currently supports **AliExpress**, **CJ Dropshipping**, **Spocket**, and **Manual** entry. More supplier platforms may be added in the future.

### What happens if an import fails?

Failed imports stay in your import list with a "Failed" status. You can click **Retry** to try again. The error message tells you what went wrong.

### Does importing a product count toward my limit if it fails?

Yes, each import job counts toward your monthly limit regardless of its final status (completed, failed, or cancelled).

### Can I connect multiple stores?

Yes, you can connect as many stores as you need. Set one as the default for quick imports, or choose a specific store when creating each import.

### How often are prices checked?

Price watches are synced automatically on a regular schedule. You can also trigger an immediate sync from the Price Watch page by clicking **Sync Now**.

### What does the price change threshold mean?

The threshold (default 10%) determines how large a price change must be before it is flagged. For example, with a 10% threshold on a $20 product, a price change to $22 (10% increase) would trigger the flag.

### Can I cancel a running import?

Yes, both pending and running imports can be cancelled from the Imports page.

### How do I downgrade my plan?

Go to **Billing** and click **Manage Subscription**. From the Stripe Customer Portal, you can change or cancel your plan. Cancellation takes effect at the end of your current billing period.

---

## Navigation Reference

| Page | What It Does |
|---|---|
| **Dashboard** | Overview of your import activity and account status |
| **Imports** | Create, view, cancel, and retry product imports |
| **Products** | Search supplier catalogs and preview products |
| **Suppliers** | Manage your supplier platform accounts |
| **Connections** | Connect and manage your dropshipping stores |
| **Price Watch** | Monitor supplier product prices |
| **Billing** | View plans, manage subscription, see usage |
| **API Keys** | Create and manage programmatic access keys |
| **Settings** | Account settings and preferences |
