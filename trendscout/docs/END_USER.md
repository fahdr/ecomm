# End User Guide

**For End Users:** This guide explains how to use TrendScout to discover winning products for your e-commerce or dropshipping business. TrendScout scans multiple data sources, scores products using AI, and helps you build a curated watchlist of the most promising opportunities.

---

## What Is TrendScout?

TrendScout is a product research tool that helps you find trending, high-potential products before your competitors. Instead of manually searching AliExpress, scrolling through TikTok, or reading Reddit threads, TrendScout does all of that automatically and ranks the results with an AI-powered scoring system.

Here is what TrendScout does for you:

- **Searches multiple data sources at once** -- AliExpress, TikTok, Google Trends, and Reddit
- **Scores every product from 0 to 100** based on social buzz, market demand, competition level, SEO potential, and business fundamentals
- **Provides AI-generated insights** including opportunity ratings, risk factors, recommended pricing, target audience profiles, and marketing angle suggestions
- **Lets you save the best products** to a watchlist for tracking and eventual import into your store

---

## Dashboard Features

When you log in to TrendScout, you will find these sections in the sidebar:

| Page | What It Does |
|------|-------------|
| **Dashboard** | Overview of your account, recent research runs, and key metrics |
| **Research** | Start new product research runs and view results |
| **Watchlist** | Manage your saved products (watching, imported, dismissed) |
| **Sources** | Configure your external data source connections |
| **History** | View past research runs and their outcomes |
| **API Keys** | Generate API keys for programmatic access (Enterprise) |
| **Billing** | Manage your subscription, view plans, and check usage |
| **Settings** | Update your account preferences |

---

## Feature Overview

### Product Research

The core feature of TrendScout. Here is how it works:

1. **Enter keywords** -- Type the product categories or niches you want to research (e.g., "wireless earbuds", "yoga mat", "LED lights").
2. **Select data sources** -- Choose which platforms to scan. Free users get AliExpress and Google Trends. Pro and Enterprise users have access to all four sources plus custom sources.
3. **Start the run** -- TrendScout kicks off a background research job. You will see the status change from "pending" to "running" to "completed".
4. **Review results** -- Each discovered product gets a composite score (0-100) and optional AI analysis.

Research runs are limited by your plan tier:
- **Free:** 5 runs per month
- **Pro:** 50 runs per month
- **Enterprise:** Unlimited

### AI Scoring

Every product discovered in a research run receives a weighted score based on five dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Social | 40% | Engagement metrics (likes, shares, views, comments, trending status) |
| Market | 30% | Search volume, order counts, and growth rate |
| Competition | 15% | Number of sellers, market saturation, average review quality |
| SEO | 10% | Keyword relevance, search position, content quality |
| Fundamentals | 5% | Price range, margin potential, shipping time, product weight |

Higher scores indicate stronger product opportunities. Products scoring 70+ are generally considered strong candidates.

### AI Analysis (Pro and Enterprise)

Pro and Enterprise users receive a detailed AI analysis for each product result:

- **Summary** -- A concise assessment of the product's dropshipping potential
- **Opportunity Score** -- A 0-100 rating of the overall opportunity
- **Risk Factors** -- Three specific risks to consider (e.g., shipping times, competition, seasonality)
- **Recommended Price Range** -- Suggested retail pricing based on market data
- **Target Audience** -- Description of the ideal buyer persona
- **Marketing Angles** -- Three suggested marketing strategies

### Watchlist

The watchlist is where you save promising products for ongoing tracking:

- **Watching** -- Products you are monitoring for potential import
- **Imported** -- Products you have already pushed to your store
- **Dismissed** -- Products you have decided against

You can add notes to each watchlist item to remember why you saved it or track price changes.

Watchlist limits by plan:
- **Free:** 25 items
- **Pro:** 500 items
- **Enterprise:** Unlimited

### Source Configuration

Under the Sources tab, you can configure your connections to external data platforms:

| Source | Description | Free Plan | Pro/Enterprise |
|--------|-------------|-----------|---------------|
| AliExpress | Product listings, prices, order counts, seller data | Available | Available |
| Google Trends | Search interest, trending topics, growth patterns | Available | Available |
| TikTok | Viral products, social engagement, trending hashtags | Not available | Available |
| Reddit | Community discussions, product recommendations, niche insights | Not available | Available |

Each source has its own settings (like region and language preferences). Your API credentials are stored securely and never displayed after entry.

### Analytics

Track your usage across the billing period:
- Research runs used vs. your plan limit
- Watchlist items count vs. capacity
- API key usage metrics (Enterprise)

---

## Subscription Tiers

| | Free | Pro | Enterprise |
|---|------|-----|-----------|
| **Price** | $0/month | $29/month | $99/month |
| **Research Runs** | 5/month | 50/month | Unlimited |
| **Data Sources** | 2 (AliExpress + Google Trends) | All 4 + custom | All sources + API |
| **AI Analysis** | Basic scoring only | Full AI-powered insights | Priority processing |
| **Watchlist Items** | 25 | 500 | Unlimited |
| **API Access** | No | Yes | Yes |
| **Trial** | -- | 14 days free | 14 days free |
| **Support** | Community | Email | Dedicated |

---

## Getting Started

### Step 1: Register

Create your account at the TrendScout dashboard. You will start on the Free plan automatically.

### Step 2: Choose a Plan

Visit the Billing page to review available plans. If you want access to all data sources and AI analysis, upgrade to Pro or Enterprise. Both paid plans include a 14-day free trial.

### Step 3: Configure Sources

Go to the Sources page and set up your data source connections. On the Free plan, AliExpress and Google Trends are available. If applicable, enter your API credentials for each source.

### Step 4: Run Research

Navigate to the Research page, enter your product keywords, select the data sources to scan, and start your research run. The run will execute in the background.

### Step 5: Review Results

Once your run completes (usually within seconds), review the results. Products are sorted by their composite score. Click on individual results to see the full AI analysis (Pro/Enterprise).

### Step 6: Add to Watchlist

Found a promising product? Click "Add to Watchlist" to save it. Add notes to remember key details. You can filter your watchlist by status (watching, imported, dismissed).

### Step 7: Import Winners

When you are ready to sell a product, mark it as "imported" in your watchlist. If you are using TrendScout as part of the dropshipping platform, import the product directly into your store.

---

## API Access

Enterprise users can access TrendScout programmatically via API keys:

1. Go to the **API Keys** page in the dashboard
2. Click "Create API Key" and give it a name
3. Copy the key immediately -- it is only shown once
4. Use the key in the `X-API-Key` header for API requests

Example API call:

```
GET /api/v1/usage
X-API-Key: your_api_key_here
```

Full API documentation is available at `http://your-trendscout-url/docs` (Swagger) or `http://your-trendscout-url/redoc` (ReDoc).

---

## Frequently Asked Questions

**How long does a research run take?**
With the default setup, research runs complete within a few seconds. With real external API integrations, expect 10-30 seconds depending on the number of sources selected.

**Can I customize the scoring weights?**
Yes. When creating a research run, advanced users can provide a `score_config` override to adjust the weight of each scoring dimension (Social, Market, Competition, SEO, Fundamentals).

**What happens when I reach my plan limit?**
You will receive a notification that your limit has been reached. You can upgrade your plan at any time from the Billing page, or wait for the next billing period when your usage resets.

**Are my source credentials secure?**
Yes. Credentials are stored securely in the database and are never returned in API responses. The dashboard only shows whether credentials have been configured (a yes/no indicator).

**Can I re-add a product I dismissed?**
Yes. If you remove a product from your watchlist (or dismiss it), you can add it back at any time from the research results.

---

## Support

- **Free plan:** Community support via documentation
- **Pro plan:** Email support
- **Enterprise plan:** Dedicated support with priority response

For technical issues or feature requests, contact the support team or file an issue in the project repository.
