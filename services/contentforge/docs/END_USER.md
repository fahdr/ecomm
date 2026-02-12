# End User Guide

**For End Users:** ContentForge transforms raw product data into polished, SEO-ready listings in seconds. Whether you paste a product URL, type in details manually, or upload a CSV file, ContentForge generates optimized titles, descriptions, meta tags, keywords, and bullet points -- all tuned to your preferred tone and style.

---

## What Is ContentForge?

ContentForge is an AI-powered content generator built for dropshipping and e-commerce sellers. Instead of spending hours writing product descriptions, you provide basic product information and ContentForge creates professional copy that is ready to publish on your store.

**What it generates:**

- **SEO Titles** -- Keyword-rich product titles optimized for search engines
- **Product Descriptions** -- Compelling copy in your chosen tone (professional, casual, luxury, playful, technical)
- **Meta Descriptions** -- 160-character summaries for search engine results
- **Keywords** -- Relevant search terms for product discoverability
- **Bullet Points** -- Scannable feature lists for product pages

**What it also does:**

- **Image Optimization** -- Automatically downloads and converts product images to WebP format for faster page loads
- **Pricing Calculator** -- Calculates optimal selling prices with markup and psychological rounding ($X.99, $X.95)

---

## Dashboard Features

After logging in at the dashboard, you have access to the following pages:

| Page | What It Does |
|------|-------------|
| **Dashboard** | Overview of your account with recent activity and key metrics |
| **Generate** | Create new content -- paste a URL, enter details manually, or upload a CSV |
| **Templates** | Browse system templates and create custom ones with your brand voice |
| **Images** | View all processed product images with format, size, and dimensions |
| **History** | Browse all past generation jobs and their results |
| **API Keys** | Create and manage API keys for programmatic access |
| **Billing** | View your current plan, manage subscription, and check usage |
| **Settings** | Update your profile and preferences |

---

## Feature Overview

### Content Generation

This is the core feature. You provide product information and ContentForge generates optimized content.

**Three ways to generate content:**

1. **From a URL** -- Paste a product page URL and ContentForge extracts product details automatically
2. **Manual Entry** -- Type in product name, price, category, and features directly
3. **CSV Import** (Pro and Enterprise) -- Upload a CSV file with multiple products for bulk generation

**How it works:**

1. Go to the **Generate** page
2. Choose your input method (URL, manual, or CSV)
3. Select a **template** to control tone and style
4. Pick which content types you want (title, description, meta tags, keywords, bullet points)
5. Click Generate
6. View your results immediately -- each content piece is editable
7. Copy the content to your store

### Image Optimization

When you generate content from a product URL that includes images, ContentForge automatically:

- Downloads the original product images
- Resizes them to optimal dimensions (800x600 by default)
- Converts them to WebP format for modern browsers
- Compresses them to reduce file size

View all your processed images on the **Images** page, which shows the original URL, optimized format, dimensions, and file size.

### Templates

Templates control the personality of your generated content. ContentForge includes system templates and lets you create custom ones.

**System Templates** (available to all users):
- **Professional** -- Clean, authoritative product descriptions
- **Casual** -- Friendly, conversational tone
- **Luxury** -- Premium, sophisticated language
- **SEO-Focused** -- Keyword-dense for maximum search visibility

**Custom Templates** (create your own):
- Choose a tone: professional, casual, luxury, playful, or technical
- Choose a style: concise, detailed, storytelling, or list-based
- Set which content types to generate
- Optionally provide a custom AI prompt for complete control

Go to the **Templates** page to manage your templates.

### Pricing Calculator

The pricing calculator helps you set optimal selling prices:

- Enter your product cost and markup percentage
- Choose a rounding strategy:
  - **$X.99** -- Creates a "deal" perception (most common in e-commerce)
  - **$X.95** -- Slightly premium feel
  - **$X.00** -- Clean whole numbers for luxury positioning
  - **Exact** -- No rounding, precise markup

---

## Subscription Tiers

| Feature | Free | Pro ($19/mo) | Enterprise ($79/mo) |
|---------|------|-------------|-------------------|
| Generations per month | 10 | 200 | Unlimited |
| Words per generation | 500 | 2,000 | Unlimited |
| AI-optimized images | 5 | 100 | Unlimited |
| System templates | Yes | Yes | Yes |
| Custom templates | No | Yes | Yes |
| Bulk import (CSV/URL) | No | Yes | Yes |
| API access | No | Yes | Yes |
| White-label output | No | No | Yes |
| Free trial | -- | 14 days | 14 days |

### When to Upgrade

- **Free to Pro**: You are generating content for more than 10 products per month, need bulk import, or want custom templates
- **Pro to Enterprise**: You need unlimited generations, API access for automation, or white-label output for clients

---

## Getting Started

### Step 1: Create Your Account

Visit the registration page and sign up with your email and a password (minimum 8 characters).

### Step 2: Choose a Plan

Start with the Free tier to try ContentForge. When ready, go to **Billing** to upgrade to Pro or Enterprise.

### Step 3: Generate Your First Content

1. Navigate to the **Generate** page
2. Enter a product name (e.g., "Wireless Bluetooth Headphones")
3. Add a price (e.g., "49.99")
4. Add a category (e.g., "Electronics")
5. Add key features (e.g., "Noise cancelling, 30-hour battery, Comfortable fit")
6. Select content types: title, description, meta_description, keywords, bullet_points
7. Click **Generate**

### Step 4: Review and Edit

ContentForge generates content instantly. You can:

- **Edit** any generated text to fine-tune the wording
- **Regenerate** specific content types if you want a different version
- **Copy** the content directly to your store's product listings

### Step 5: Set Up Templates

If you generate content frequently, create a custom template to maintain a consistent voice:

1. Go to the **Templates** page
2. Click **Create Template**
3. Name it (e.g., "My Store Voice")
4. Choose a tone (casual, professional, etc.) and style (concise, detailed, etc.)
5. Save and select it when generating future content

---

## API Access

Pro and Enterprise users can access ContentForge programmatically using API keys.

### Creating an API Key

1. Go to **API Keys** in the dashboard
2. Click **Create Key**
3. Name your key and choose permission scopes (read, write)
4. **Copy the key immediately** -- it will not be shown again

### Using the API

Authenticate by including the `X-API-Key` header in your requests:

```
X-API-Key: cf_live_your_key_here
```

Or use JWT authentication with the `Authorization` header:

```
Authorization: Bearer your_jwt_token_here
```

### Key Endpoints

| Action | Method | Path |
|--------|--------|------|
| Generate content | POST | `/api/v1/content/generate` |
| Bulk generate | POST | `/api/v1/content/generate/bulk` |
| List jobs | GET | `/api/v1/content/jobs` |
| Get job details | GET | `/api/v1/content/jobs/{job_id}` |
| List templates | GET | `/api/v1/templates/` |
| Check usage | GET | `/api/v1/usage` |

Full API documentation is available at: **http://localhost:8102/docs**

---

## Support

### Common Issues

**"Monthly generation limit reached"**
You have used all your generations for the current billing period. Upgrade your plan or wait until the next billing cycle (1st of each month UTC).

**"Image limit would be exceeded"**
You have reached your monthly image processing quota. Upgrade your plan for more image processing capacity.

**Content does not match my brand voice**
Create a custom template with your preferred tone and style settings. Use the prompt override feature for complete control over the AI's writing style.

**I lost my API key**
API keys are shown only once at creation for security. Revoke the lost key and create a new one from the API Keys page.

### Getting Help

- **API Documentation**: Available at `/docs` on your backend URL
- **Dashboard**: In-app tooltips and labels guide you through each feature
- **System Status**: The health endpoint at `/api/v1/health` shows service status
