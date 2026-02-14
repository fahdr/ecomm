# RankPilot End User Guide

> Part of [RankPilot](README.md) documentation

## What Is RankPilot?

RankPilot is an **Automated SEO Engine** that helps you boost your website's search engine rankings. Instead of spending hours manually optimizing your site, RankPilot automates the process -- generating blog content, tracking where your keywords rank, auditing your site for SEO issues, and creating structured data that makes your pages stand out in search results.

Whether you run an e-commerce store, a blog, or a business website, RankPilot gives you the tools to compete for top search positions without needing to be an SEO expert.

---

## Features

### Site Management

Register your website domains in RankPilot to start tracking and optimizing. After adding a domain, verify ownership to unlock all features. You can manage multiple sites (depending on your plan) and track SEO performance for each one independently.

**What you can do:**
- Add your website domain (e.g., `mystore.com`)
- Verify domain ownership to activate SEO features
- Set your XML sitemap URL for better crawl optimization
- View all your registered sites in one place

### AI Blog Posts

Create SEO-optimized blog content using AI. Provide a title and target keywords, and RankPilot generates a full blog post with proper headings, keyword integration, and meta descriptions -- all optimized for search engines.

**What you can do:**
- Create blog posts with a title and optional target keywords
- Use AI to automatically generate SEO-optimized content
- Manage post lifecycle: draft, published, and archived statuses
- View and edit generated content, meta descriptions, and keywords
- Track word count for each post

**How AI generation works:**
1. Create a new blog post with a title and target keywords.
2. Click "Generate" to have AI fill in the content.
3. Review and edit the generated content as needed.
4. Publish the post when you are satisfied.

### Keyword Rank Tracking

Monitor where your target keywords rank in search engine results over time. See your current position, previous position, search volume, and difficulty score for each keyword.

**What you can do:**
- Add keywords you want to track for each site
- View current and previous search result positions
- See rank changes (improvements or drops) at a glance
- Monitor search volume and keyword difficulty
- Refresh rank data on demand

**Understanding rank data:**
- **Current Rank**: Your keyword's current position in search results (1 = top spot)
- **Previous Rank**: Where you ranked before the last check (shows trend)
- **Search Volume**: How many people search for this keyword monthly
- **Difficulty**: How competitive this keyword is (0-100, higher = harder)

### SEO Audits

Run automated health checks on your website to identify SEO issues and get actionable recommendations. Each audit produces a score from 0 to 100, along with a list of specific problems found and what to do about them.

**What you can do:**
- Run an SEO audit on any of your registered sites
- Get a health score from 0 to 100
- View categorized issues (critical, warning, informational)
- Get specific, actionable recommendations for improvement
- Track your score over time by running audits regularly

**Issue categories:**
- **Meta Tags**: Missing or incorrect title tags, meta descriptions, Open Graph tags
- **Performance**: Slow page load times, uncompressed images, missing caching
- **Content**: Thin content, missing headings, duplicate content
- **Technical**: Multiple H1 tags, outdated sitemaps, broken links
- **Mobile**: Missing viewport configuration, non-responsive design

### Schema Markup (JSON-LD)

Generate structured data markup that helps search engines understand your page content. Proper schema markup can enable rich snippets in search results -- star ratings, prices, FAQ dropdowns, and more.

**Supported schema types:**
- **Product**: Product name, price, availability, ratings, brand
- **Article**: Blog/news article with author, publisher, dates
- **FAQ**: Frequently asked questions with expandable answers in search results
- **Breadcrumb**: Navigation path showing page hierarchy
- **Organization**: Company information, contact details, social profiles

**What you can do:**
- Create schema markup configurations for each page type
- Use default templates or customize the JSON-LD manually
- Preview the generated `<script>` tag ready for your HTML
- Enable/disable individual schema configs
- Copy the rendered script tag and paste it into your website

---

## Subscription Tiers

### Free ($0/month)

Perfect for getting started with SEO optimization.

- 2 AI blog posts per month
- 20 keywords tracked
- 1 site
- Basic schema markup

### Pro ($29/month)

For serious store owners who want comprehensive SEO tools.

- 20 AI blog posts per month
- 200 keywords tracked
- 5 sites
- Advanced JSON-LD schema markup
- Content gap analysis
- 14-day free trial

### Enterprise ($99/month)

For agencies and large stores needing unlimited access.

- Unlimited AI blog posts
- Unlimited keywords tracked
- Unlimited sites
- Full API access for integrations
- Custom schema templates
- 14-day free trial

---

## Getting Started

### Step 1: Create Your Account

1. Go to the RankPilot dashboard.
2. Click **Register** and enter your email and password.
3. You will be logged in automatically with a free account.

### Step 2: Add Your Website

1. Navigate to **Sites** in the sidebar.
2. Click **Add Site** and enter your domain (e.g., `mystore.com`).
3. Optionally add your sitemap URL (e.g., `https://mystore.com/sitemap.xml`).
4. Click **Verify** to confirm domain ownership.

### Step 3: Create Your First Blog Post

1. Navigate to **Blog Posts** in the sidebar.
2. Click **Create Post** and enter a title (e.g., "10 Best Running Shoes for 2025").
3. Add target keywords (e.g., "running shoes", "best running shoes", "athletic footwear").
4. Click **Generate with AI** to have content automatically created.
5. Review the generated content and meta description.
6. Edit as needed and click **Publish** when ready.

### Step 4: Start Tracking Keywords

1. Navigate to **Keywords** in the sidebar.
2. Select the site you want to track keywords for.
3. Click **Add Keyword** and enter a search term (e.g., "best running shoes").
4. Repeat for all keywords you want to monitor.
5. Click **Refresh Ranks** to get initial position data.
6. Check back regularly to see how your rankings change over time.

### Step 5: Run an SEO Audit

1. Navigate to **Audits** in the sidebar.
2. Select your site and click **Run Audit**.
3. Review your health score (0-100).
4. Look at the issues list -- fix critical issues first, then warnings.
5. Follow the specific recommendations provided.
6. Run another audit after making changes to see your score improve.

### Step 6: Add Schema Markup

1. Navigate to **Schema** in the sidebar.
2. Select your site and choose a page type (e.g., "Product").
3. Review the generated JSON-LD template.
4. Customize the template with your actual product/page data.
5. Click **Preview** to see the rendered script tag.
6. Copy the `<script>` tag and paste it into your website's HTML.

### Step 7: Upgrade When Ready

1. Navigate to **Billing** in the sidebar.
2. Compare plans and choose the one that fits your needs.
3. Click **Subscribe** and complete the checkout process.
4. Your new limits take effect immediately.

---

## Managing API Keys

If you are on the Pro or Enterprise plan, you can generate API keys for programmatic access:

1. Navigate to **API Keys** in the sidebar.
2. Click **Create API Key** and give it a descriptive name.
3. Copy the raw key immediately -- it is only shown once.
4. Use the key in your API requests via the `X-API-Key` header.

---

## Frequently Asked Questions

**How often should I run SEO audits?**
We recommend running an audit at least once a week, especially after making changes to your site. This helps you track improvements over time.

**How does the AI blog generation work?**
You provide a title and target keywords. The AI generates a full blog post with proper headings, keyword integration, and a meta description optimized for search engines. You can edit the content before publishing.

**What happens when I reach my plan limit?**
You will see a message indicating you have reached your monthly limit (for blog posts) or total limit (for keywords). Upgrade your plan to continue creating content or tracking more keywords.

**Can I downgrade my plan?**
Yes. Go to **Billing** and manage your subscription through the customer portal. Downgrades take effect at the end of your current billing period.

**Do I need technical knowledge to use schema markup?**
No. RankPilot generates the JSON-LD templates automatically. You just need to copy the rendered script tag and paste it into your website's HTML. If you use a CMS like WordPress or Shopify, look for a "custom code" or "header scripts" section in your theme settings.

**How accurate is the keyword ranking data?**
Ranking data is updated when you click "Refresh Ranks" or when the system runs periodic checks. Positions may vary slightly due to personalization and location-based search results.

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
