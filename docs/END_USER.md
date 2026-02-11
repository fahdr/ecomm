# End User Guide

**For End Users:**
This guide explains what the Dropshipping Platform does, what features are available, and how to use them to run your online store.

## What Is This Platform?

The Dropshipping Platform is an all-in-one tool for running an online dropshipping business. It handles everything from setting up your store and managing products to processing customer orders, tracking performance with analytics, and customizing your store's look and feel — so you can focus on growing your business.

## Two Interfaces

### Dashboard (For Store Owners)

The Dashboard is your control center at `http://localhost:3000`. From here you can:

- **Create and configure stores** — Set up multiple stores, each with its own name, niche, and unique web address
- **Manage products** — Add products with titles, descriptions, pricing, images, variants (sizes, colors), and SEO metadata
- **Process orders** — View incoming orders, mark as paid, ship with tracking numbers, and mark as delivered
- **Customize your storefront** — Choose from 11 preset themes, configure block layouts, adjust colors, typography, and animations
- **Track analytics** — Monitor revenue, order trends, product performance, and customer metrics with visual charts
- **Manage customers** — View customer reviews, segments, and refund requests
- **Run promotions** — Create discount codes, gift cards, and upsell recommendations
- **Export data** — Download orders, products, and customer data as CSV files
- **Team collaboration** — Invite team members and configure webhook integrations
- **Monitor inventory** — Get automatic low-stock alerts when products are running low

### Storefront (For Your Customers)

The Storefront is what your customers see when they visit your store. Each store gets its own themed web experience. Customers can:

- **Browse products** — View your catalog with animated product grids, category pages, and search with autocomplete
- **View product details** — See images (with hover zoom), variants, pricing, reviews, and related products
- **Shop with a cart** — Add items, adjust quantities, and check out securely via Stripe
- **Create an account** — Register, manage addresses, view order history, and maintain a wishlist
- **See a themed experience** — Each store has a unique visual identity with custom colors, fonts, and page layouts

## Feature Overview

### Store Management

- **Multi-store support** — Create and manage multiple stores from a single dashboard account
- **Store settings** — Configure name, niche, description, status (active/paused), custom domain, tax settings, and currency
- **Subscription plans** — Choose from Starter, Growth, or Pro plans with different store/product limits

### Product Management

- **Full CRUD** — Create, read, update, and delete products with rich details
- **Variants** — Support for sizes, colors, and other options with individual pricing and inventory tracking
- **Image upload** — Upload product images directly from the dashboard
- **Categories** — Organize products into categories for easy browsing
- **Search & filter** — Search products by title, filter by status (active/draft/archived)
- **Bulk operations** — Perform actions on multiple products at once

### Order Management

- **Order lifecycle** — Track orders from pending → paid → shipped → delivered
- **Fulfillment** — Enter tracking numbers and carrier info, mark orders as shipped or delivered
- **Internal notes** — Add private notes to orders for your team (not visible to customers)
- **Refunds** — Process full or partial refunds
- **Shipping addresses** — View customer shipping details on each order
- **CSV export** — Download your order history as a spreadsheet

### Theme Engine

Your store's appearance is fully customizable:

- **11 preset themes** — Choose from Frosted (modern teal), Midnight (dark cyan), Botanical (green organic), Neon (hot pink electric), Luxe (gold premium), Playful (orange fun), Industrial (charcoal raw), Coastal (ocean blue), Monochrome (black editorial), Cyberpunk (purple neon), and Terracotta (earthy warm)
- **13 block types** — Build your homepage with configurable blocks:
  - **Hero Banner** — Large hero section with gradient, image, or product showcase backgrounds
  - **Featured Products** — Auto-populated grid of your best products
  - **Categories Grid** — Browse-by-category section
  - **Product Carousel** — Auto-scrolling horizontal product showcase
  - **Testimonials** — Customer quotes displayed as cards or a slider
  - **Countdown Timer** — Sale or launch countdown with days/hours/minutes/seconds
  - **Video Banner** — YouTube or Vimeo video embed with text overlay
  - **Trust Badges** — Icons for free shipping, secure checkout, money-back guarantee
  - **Reviews** — Customer review showcase
  - **Newsletter** — Email signup section
  - **Custom Text** — Freeform text/HTML content
  - **Image Banner** — Static image with overlay text
  - **Spacer** — Adjustable vertical spacing
- **Color & typography controls** — Customize primary/accent colors, heading/body fonts, font weights, letter spacing, and line height
- **Block config editor** — Full configuration panel for each block (not just on/off toggles)

### Dashboard Features

- **Platform home** — Aggregate KPIs across all your stores (total revenue, orders, products, active stores), with individual store cards
- **Store overview** — KPI dashboard with revenue, orders, products, and conversion metrics plus recent orders and quick actions
- **Command palette** — Press `Ctrl+K` (or `Cmd+K` on Mac) to quickly navigate to any page, search stores, or trigger actions
- **Inventory alerts** — Automatic warning cards on your store overview when products have fewer than 5 units in stock
- **Notification badges** — Unread notification count on the sidebar, pending order count on the Orders nav item
- **Analytics** — Revenue charts, order trends, product performance tables, and customer metrics with date range selection
- **CSV export** — One-click export buttons on orders and products pages

### Customer Experience

Your customers enjoy a premium shopping experience:

- **Animated pages** — Smooth fade-in, stagger, and slide animations throughout the storefront
- **Product badges** — "New" badges for recently added products, "Sale" badges for discounted items
- **Recently viewed** — Automatic recently viewed products section on product detail pages
- **Search autocomplete** — Real-time search suggestions with product thumbnails as customers type
- **Customer accounts** — Registration, login, order history, address book, and wishlist management
- **Mobile responsive** — Spring-based mobile menu with smooth animations

### Marketing & Promotions

- **Discount codes** — Create percentage or fixed-amount discounts with optional expiry dates
- **Gift cards** — Issue and manage gift cards for your store
- **Upsell recommendations** — Configure cross-sell product suggestions
- **A/B tests** — Run experiments to optimize your store
- **Email automation** — Configure email templates and flows
- **Reviews** — Customer product reviews with moderation tools
- **Customer segments** — Group customers by behavior for targeted marketing

### Operations

- **Supplier management** — Track supplier information and relationships
- **Fraud detection** — Monitor orders for suspicious activity
- **Tax configuration** — Set up tax rules by region
- **Currency settings** — Configure store currency
- **Custom domain** — Connect your own domain name to your store
- **Team management** — Invite team members with role-based access
- **Webhooks** — Configure external integrations via webhook endpoints

## Subscription Tiers

The platform offers three plans:

| Plan | Target User |
|------|------------|
| **Starter** | New entrepreneurs getting started with dropshipping |
| **Growth** | Growing businesses that need more stores and products |
| **Pro** | Established sellers who want full automation and advanced features |

All plans include a 14-day free trial. You can upgrade, downgrade, or cancel at any time through the billing page in your dashboard.

## Demo Mode

A pre-configured demo store ("Volt Electronics") is available for exploring the platform. It comes with 12 products, customers, orders, reviews, and a fully themed storefront.

### Demo Credentials

| Role | Email | Password | Where to log in |
|------|-------|----------|----------------|
| **Store Owner** | `demo@example.com` | `password123` | Dashboard at `http://localhost:3000` |
| **Customer (Alice)** | `alice@example.com` | `password123` | Storefront at `http://localhost:3001?store=volt-electronics` |
| **Customer (Bob)** | `bob@example.com` | `password123` | Storefront at `http://localhost:3001?store=volt-electronics` |
| **Customer (Carol)** | `carol@example.com` | `password123` | Storefront at `http://localhost:3001?store=volt-electronics` |

### What's in the Demo Store

- **12 products** across 6 categories (Laptops, Smartphones, Audio, Accessories) with images, variants, and reviews
- **4 orders** showing the full lifecycle: pending → paid → shipped → delivered
- **Cyberpunk theme** with countdown timer, product carousel, testimonials, and trust badges
- **5 discount codes** you can try: `WELCOME10` (10% off), `SUMMER25` (25% off), `FLAT20` ($20 off $100+)
- **3 customer accounts** with saved addresses, wishlists, and order history

### Setting Up the Demo

If the demo data isn't already loaded, a developer or admin can seed it by running:

```bash
npx tsx scripts/seed.ts
```

This only needs to be run once — the script is safe to re-run without creating duplicates.

## Getting Started

1. **Register** — Create an account with your email and password at the Dashboard
2. **Choose a plan** — Pick Starter, Growth, or Pro (free trial included) on the Pricing page
3. **Create your store** — Give it a name, pick a niche, and add a description
4. **Pick a theme** — Browse 11 preset themes and customize colors, fonts, and blocks
5. **Add products** — Create products with images, variants, and pricing
6. **Organize** — Set up categories and arrange your homepage blocks
7. **Launch** — Set your store to "active" and share the storefront URL with customers
8. **Monitor** — Track orders, revenue, and inventory from the dashboard
9. **Optimize** — Use analytics, A/B tests, and promotions to grow your business

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` / `Cmd+K` | Open command palette (quick navigation) |
| `Escape` | Close modals and command palette |

## Support

For questions, issues, or feedback, please reach out through the platform's support channels (details will be provided at launch).
