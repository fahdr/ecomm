# py-suppliers End User Guide

## What Is Supplier Integration?

The supplier integration system connects your dropshipping store to wholesale product suppliers like AliExpress and CJDropship. Instead of buying inventory upfront, you browse supplier catalogs, import products you want to sell, and when a customer places an order, the supplier ships directly to them.

This system handles:

- **Product discovery** -- Search supplier catalogs by keyword or category
- **Product import** -- Pull in product details, images, variants, and pricing automatically
- **Price optimization** -- Calculate your retail price with automatic markup and charm pricing
- **Image processing** -- Download and optimize product images for your storefront

---

## Supported Suppliers

### AliExpress

AliExpress is the world's largest dropshipping marketplace, operated by Alibaba Group. It offers access to millions of products from Chinese manufacturers at wholesale prices.

**Strengths:**
- Massive product selection across every category
- Very competitive pricing (often the lowest cost per unit)
- Free standard shipping on many items
- Buyer protection program

**Considerations:**
- Shipping typically takes 12-25 days from China
- Communication with sellers may have language barriers
- Product quality can vary between sellers

**Product categories available:**
- Electronics (earbuds, chargers, projectors, smart watches, keyboards, action cameras)
- Fashion (sunglasses, shirts, bags, sneakers, jewelry, pants)
- Home & Garden (LED strips, milk frothers, wall shelves, desk organizers, oil diffusers, portable blenders)
- Beauty & Health (jade rollers, scalp massagers, vitamin C serums, teeth whitening kits, derma rollers, silk pillowcases)

### CJDropship

CJDropship is a dropshipping fulfillment platform that offers US and EU warehouse options for faster delivery times. They also provide quality inspection and branded packaging services.

**Strengths:**
- US/EU warehouse fulfillment (3-10 day delivery)
- Quality inspection before shipping
- Branded/custom packaging available
- No minimum order quantities

**Considerations:**
- Smaller catalog compared to AliExpress
- Slightly higher unit costs (offset by faster shipping)
- Requires separate account registration

**Product categories available:**
- Electronics (wireless chargers, FM transmitters, power banks, ring lights)
- Fashion (leather belts, compression leggings, minimalist watches, toiletry bags)
- Home & Garden (kitchen utensil sets, spice racks, watering globes, laundry baskets, shower caddies)
- Beauty & Health (ice rollers, LED face masks, whitening strips, nail drills, scalp brushes)

---

## How to Search for Products

Search for products by typing keywords related to what you want to sell. The system searches across product titles, descriptions, and categories.

**Effective search tips:**

| Search Query | What You Will Find |
|-------------|-------------------|
| `"wireless earbuds"` | Bluetooth earbuds and TWS headphones |
| `"electronics"` | All products in the electronics category |
| `"beauty"` | Skincare tools, serums, massagers, and beauty devices |
| `"leather bag"` | Genuine leather crossbody bags and accessories |
| `"kitchen"` | Kitchen utensils, organizers, and gadgets |
| `"yoga"` | Yoga-related fitness products (leggings, mats, etc.) |

Search is case-insensitive, so `"Earbuds"`, `"earbuds"`, and `"EARBUDS"` all return the same results.

### Importing by URL

If you find a product on a supplier's website, you can import it directly by pasting the product URL. The system automatically extracts the product ID and pulls in all the details.

**Supported URL formats:**

AliExpress:
- `https://www.aliexpress.com/item/1005006841237901.html`
- `https://aliexpress.com/i/1005006841237901.html`

CJDropship:
- `https://cjdropshipping.com/product/CJ-ELEC-2891734`
- `https://cjdropshipping.com/product_detail/p-CJ-ELEC-2891734`

---

## Understanding Product Data

When you import a product, you receive comprehensive information:

### Basic Information
- **Title** -- The product name as listed by the supplier
- **Description** -- Full product description (may include specifications, features, and materials)
- **Price** -- The supplier's wholesale cost (what you pay per unit)
- **Currency** -- Always displayed in USD

### Images
- Multiple product images from different angles
- Images are automatically optimized for web display (resized to max 1200px width, compressed for fast loading)
- Thumbnails (300x300px) are generated for product listings and cart views

### Variants
Products may have multiple variants (options). Each variant represents a specific purchasable combination:

| Example Product | Variant Examples |
|----------------|-----------------|
| TWS Earbuds | Color: Black, Color: White, Color: Navy Blue |
| Linen Shirt | Color: Khaki + Size: M, Color: Khaki + Size: L, Color: White + Size: M |
| Cuban Link Chain | Width: 5mm + Length: 50cm, Width: 7mm + Length: 50cm |

Each variant has its own:
- **Price** -- May differ from the base price (e.g., larger sizes cost more)
- **SKU** -- Unique identifier for ordering from the supplier
- **Stock level** -- Number of units available (when reported by the supplier)

### Shipping Information
- **Estimated delivery time** -- Range in days (e.g., 12-20 days)
- **Shipping cost** -- Per-item shipping fee (many items ship free)
- **Shipping method** -- e.g., "AliExpress Standard Shipping", "ePacket", "CJ Packet"
- **Ships from** -- Origin warehouse (CN = China, US = United States)

### Customer Ratings
- **Average rating** -- Star rating from 0 to 5
- **Review count** -- Total number of customer reviews
- **Positive percentage** -- Percentage of positive reviews (when available)

---

## How Pricing Works

The system provides three pricing tools to help you set profitable and attractive retail prices.

### 1. Markup Calculation

Add your profit margin on top of the supplier cost:

| Supplier Cost | Markup % | Your Retail Price |
|--------------|----------|-------------------|
| $10.00 | 100% | $20.00 |
| $18.74 | 150% | $46.85 |
| $5.89 | 200% | $17.67 |

**Typical markup ranges by category:**
- Electronics: 80-150% markup
- Fashion: 100-200% markup
- Home & Garden: 100-180% markup
- Beauty & Health: 150-300% markup

### 2. Psychological (Charm) Pricing

After applying markup, the system can automatically adjust prices to more attractive price points that improve conversion rates:

| Calculated Price | Charm Price | Rule Applied |
|-----------------|-------------|--------------|
| $8.42 | $7.99 | Under $10: round down to .99 |
| $30.12 | $29.97 | $10-$99: round down to .97 |
| $149.50 | $148.99 | $100+: round down to .99 |

Research shows that prices ending in .97 or .99 are perceived as significantly lower than rounded prices, even when the actual difference is small.

### 3. Compare-At (Strikethrough) Pricing

Create a "was" price to show customers the discount they are receiving:

| Your Retail Price | Discount Shown | Compare-At Price Displayed |
|------------------|----------------|---------------------------|
| $29.99 | 30% off | ~~$42.84~~ $29.99 |
| $20.00 | 50% off | ~~$40.00~~ $20.00 |
| $10.00 | 25% off | ~~$13.33~~ $10.00 |

This is a common e-commerce practice that creates urgency and perceived value.

---

## Image Processing

Product images from suppliers are automatically processed for your store:

### Optimization
- **Resizing:** Images wider than 1200 pixels are scaled down proportionally. Smaller images are not upscaled.
- **Compression:** JPEG quality is set to 85% by default, balancing visual quality with file size.
- **Format conversion:** Images with transparency (PNG with alpha channel) are composited onto a white background and saved as JPEG for broad compatibility.

### Thumbnails
- Default size: 300x300 pixels
- Aspect ratio is always preserved (no stretching or distortion)
- Used in product listings, search results, and shopping cart

### Why This Matters
Optimized images load faster, which:
- Improves your store's page speed score
- Reduces bounce rates (visitors leaving before the page loads)
- Improves your SEO ranking (search engines reward fast sites)
- Saves bandwidth costs

---

## Choosing Between Suppliers

Use this decision guide to pick the right supplier for each product:

| If you need... | Choose | Why |
|----------------|--------|-----|
| Lowest possible cost | AliExpress | Widest selection, most competitive pricing |
| Fast shipping (US customers) | CJDropship | US warehouse, 3-10 day delivery |
| Fast shipping (EU customers) | CJDropship | EU warehouse options available |
| Branded packaging | CJDropship | Custom packaging services |
| Maximum product variety | AliExpress | Millions of products across all categories |
| Quality inspection | CJDropship | Pre-shipment inspection services |
| Free shipping | Either | Both offer free shipping on many items |

**Multi-supplier strategy:** Many successful dropshippers use both suppliers. Source high-volume, time-sensitive products from CJDropship (faster shipping improves customer satisfaction) and source niche or low-volume products from AliExpress (wider catalog, lower costs).

---

## Frequently Asked Questions

### Do I need API keys to get started?

No. The system includes a demo mode with 42 realistic products (24 from AliExpress, 18 from CJDropship) that lets you explore features, set up your store, and test workflows before connecting to real supplier APIs.

### How often is product data updated?

In demo mode, product data is static and deterministic. When connected to real supplier APIs (future feature), product data will be refreshed on demand when you search or view a product.

### Can I import a product by pasting its URL?

Yes. Paste any AliExpress or CJDropship product URL and the system will automatically extract the product ID and import all details, images, and variants.

### What happens to product images?

Images are automatically downloaded from the supplier, resized to web-friendly dimensions (max 1200px wide), compressed for fast loading, and thumbnailed (300x300px) for product listings. Transparency is handled by compositing onto a white background.

### How is my retail price calculated?

You set a markup percentage (e.g., 100% doubles the supplier cost). The system then optionally applies psychological pricing to round to an attractive price point (e.g., $29.97 instead of $30.12). You can also generate a compare-at price to show a strikethrough discount.

### What product categories are available?

Both suppliers cover Electronics, Fashion, Home & Garden, and Beauty & Health. Specific products range from wireless earbuds and smart watches to leather bags, kitchen tools, skincare devices, and silk pillowcases.

### Can I sell products from multiple suppliers in one store?

Yes. The system normalizes all product data into a common format regardless of which supplier it comes from. Your customers see a unified storefront; the supplier source is tracked internally for order fulfillment.

### What if a product is out of stock?

Stock levels are reported per variant when available from the supplier. Products with zero stock for a variant will show as unavailable. Real-time stock monitoring is planned for a future update.
