# End User Guide

## What Is SpyDrop?

SpyDrop is a **Competitor Intelligence** tool designed for dropshippers and e-commerce sellers. It automates the process of monitoring your competitors so you can stay ahead of market changes without manually checking competitor stores every day.

SpyDrop watches your competitors for you and tells you when something important happens -- a price drop, a new product launch, or a product going out of stock. It can even find the original suppliers behind competitor products so you can source the same items at cost.

---

## Features

### Competitor Monitoring

Add competitor store URLs and SpyDrop will automatically scan them on a regular schedule. You can monitor stores running on Shopify, WooCommerce, or any custom e-commerce platform.

- **Add competitor stores** by name and URL
- **Choose the platform** (Shopify, WooCommerce, or Custom)
- **Pause or resume** monitoring for any competitor at any time
- **View scan history** to see what changed during each scan
- **Platform detection** helps SpyDrop use the best scanning strategy

### Product Tracking

Every time SpyDrop scans a competitor store, it discovers their products and tracks them over time. You get a complete picture of what your competitors are selling and how their pricing changes.

- **Automatic product discovery** during scans
- **Price history** for every tracked product (see how prices changed over time)
- **Cross-competitor product view** to browse all products from all competitors in one place
- **Filter by status** (active products vs. removed products)
- **Sort by price, date, or name** to find what matters most to you
- **Mini price charts** show price trends at a glance on each product card

### Price Alerts

Set up alerts and SpyDrop will notify you when your competitors make important changes. Stop manually checking stores -- let the alerts come to you.

- **Price drop alerts** -- get notified when a competitor lowers their prices (with configurable threshold)
- **Price increase alerts** -- know when competitors raise their prices (opportunity to capture their customers)
- **New product alerts** -- find out immediately when competitors add new products
- **Out-of-stock alerts** -- discover when competitor products become unavailable
- **Back-in-stock alerts** -- track when previously removed products re-appear

### Reverse Source Finding

One of SpyDrop's most powerful features is finding where your competitors source their products. SpyDrop matches competitor products to potential suppliers and calculates your potential profit margin.

- **Supplier matching** across major platforms (AliExpress, DHgate, 1688, Alibaba, Banggood, and more)
- **Confidence scoring** tells you how likely each match is correct (0-100%)
- **Margin calculation** shows your potential profit if you sell the same product
- **Multiple matches per product** so you can compare suppliers and find the best deal

---

## Subscription Tiers

SpyDrop offers three subscription plans to fit different needs:

### Free -- $0/month
Perfect for getting started and trying out SpyDrop.
- Monitor up to **3 competitor stores**
- Track up to **50 products**
- **Weekly** scan frequency
- Basic product tracking
- No price alerts
- No source finding

### Pro -- $29/month
For serious dropshippers who need daily intelligence.
- Monitor up to **25 competitor stores**
- Track up to **2,500 products**
- **Daily** scan frequency
- Price drop and new product alerts
- Reverse source finding
- Full price history
- API access for integrations
- **14-day free trial**

### Enterprise -- $99/month
For agencies and power users with unlimited needs.
- **Unlimited** competitor stores
- **Unlimited** products tracked
- **Hourly** scan frequency
- All alert types + API-delivered alerts
- Bulk source finding
- Full API access
- Priority support
- **14-day free trial**

---

## Getting Started

### Step 1: Create Your Account

Visit the SpyDrop dashboard and register with your email address and a password (minimum 8 characters). You will be logged in immediately with a free account.

- **Dashboard:** http://localhost:3105/register
- You can also access SpyDrop from the dropshipping platform dashboard if it is connected

### Step 2: Add Your First Competitor

Navigate to the **Competitors** page from the sidebar and click **Add Competitor**. Enter:

1. **Store Name** -- a label to identify this competitor (e.g., "Rival Gadgets")
2. **Store URL** -- the full URL of the competitor's store (e.g., `https://rival-gadgets.com`)
3. **Platform** -- select Shopify, WooCommerce, or Custom depending on what platform they use

Click **Add Competitor** and SpyDrop will start tracking them. You can add up to 3 competitors on the Free plan.

### Step 3: Trigger a Scan

Once you have added a competitor, you can trigger a scan from the **Scans** page. The scan will crawl the competitor's store and discover their product catalog, prices, and availability.

After the scan completes, you will see:
- **New products found** -- items that were not in the catalog before
- **Removed products** -- items that are no longer available
- **Price changes** -- products whose prices went up or down

### Step 4: Browse Products

Go to the **Products** page to see all tracked products from all your competitors in one place. Use the filters to narrow down results:

- **Status filter:** Show only "Active" products or only "Removed" products
- **Sort options:** Sort by last seen date, first seen date, price (low to high), or title (A-Z)
- **Price history:** Click "View History" on any product to see its complete price timeline

### Step 5: Set Up Alerts (Pro and Enterprise)

On the **Alerts** page, create alerts to be notified when important changes happen:

1. Choose an **alert type** (price drop, new product, out of stock, etc.)
2. Optionally scope it to a **specific competitor** or **specific product**
3. Set a **threshold** for price-based alerts (e.g., notify when price drops more than 10%)

SpyDrop will check your alerts after every scan and notify you when conditions are met.

### Step 6: Find Suppliers (Pro and Enterprise)

On the **Sources** page, select a competitor product and click **Find Sources**. SpyDrop will search major supplier platforms and return matches ranked by confidence score, with calculated profit margins.

Use this information to:
- Source the same products your competitors sell
- Compare supplier prices to find the best deal
- Calculate your potential profit margin before placing orders

### Step 7: Upgrade Your Plan (Optional)

If you need more competitors, faster scans, or access to alerts and source finding, visit the **Billing** page to upgrade to Pro ($29/mo) or Enterprise ($99/mo). Both paid plans come with a **14-day free trial**.

---

## Frequently Asked Questions

**How often are competitor stores scanned?**
It depends on your plan: weekly for Free, daily for Pro, and hourly for Enterprise. You can also trigger manual scans at any time.

**Can I monitor stores on any platform?**
SpyDrop supports Shopify, WooCommerce, and custom stores. Select the platform when adding a competitor so SpyDrop can use the best scanning strategy.

**What happens when I delete a competitor?**
All data associated with that competitor is permanently deleted, including tracked products, price history, scan results, alerts, and source matches. This action cannot be undone.

**Is my data private?**
Yes. Each user can only see their own competitors and products. There is no cross-user data access.

**Can I use SpyDrop with my own tools?**
Yes. Pro and Enterprise plans include API access. Generate an API key in the **API Keys** page and authenticate with the `X-API-Key` header to access all SpyDrop endpoints programmatically.

**What if I reach my plan limit?**
You will see an error message when trying to add more competitors than your plan allows. Upgrade to a higher tier or delete existing competitors to make room.
