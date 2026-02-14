# End User Guide

**For End Users:** This guide explains how to use ShopChat to add an intelligent AI shopping assistant to your e-commerce store. Learn how to set up chatbots, build a knowledge base, monitor conversations, customize the widget, and track performance -- all through the ShopChat dashboard.

---

## What Is ShopChat?

ShopChat is an AI-powered chat widget that you embed on your e-commerce store. It answers customer questions 24/7, recommends products from your catalog, and provides support based on your policies and FAQs -- all without requiring you to be online.

**How it works:**
1. You create a chatbot and customize its personality and appearance.
2. You build a knowledge base with your product catalog, shipping policies, FAQs, and more.
3. You copy a small code snippet and paste it into your website.
4. Visitors open the chat widget and ask questions. The AI responds using your knowledge base.
5. You review conversations, customer satisfaction scores, and analytics on the dashboard.

---

## Features

### Chatbot Configuration

Create multiple chatbots, each with its own personality and settings:

- **Name**: Give your chatbot a recognizable name (e.g., "Store Assistant", "Sales Helper").
- **Personality**: Choose a style for your chatbot's responses:
  - `friendly` -- Warm and approachable ("Great question!")
  - `professional` -- Formal and polished ("Thank you for your inquiry.")
  - `casual` -- Relaxed and informal ("Hey!")
  - `helpful` -- Direct and action-oriented ("I'd be happy to help!")
- **Welcome Message**: The first message visitors see when they open the chat (e.g., "Hi there! How can I help you today?").
- **Theme Configuration**: Customize the widget's appearance to match your store:
  - Primary color (e.g., `#6366f1`)
  - Text color
  - Position (bottom-right or bottom-left)
  - Size (small, medium, or large)
- **Active/Inactive Toggle**: Pause a chatbot without deleting it.

### Knowledge Base

The knowledge base is the "brain" of your chatbot. The more information you add, the better your chatbot answers customer questions.

**Source types you can add:**
- **Product Catalog**: Product names, descriptions, prices, and URLs. When a customer asks about products, the chatbot can suggest matching items with links.
- **Policy Pages**: Shipping policy, return policy, privacy policy. Customers frequently ask about these.
- **FAQs**: Common questions and answers specific to your business.
- **Custom Text**: Any information you want the chatbot to know -- store hours, contact info, brand story.
- **URLs**: Import content from existing web pages.

**Plan limits:**
- Free: 10 knowledge base pages
- Pro: 500 pages (full catalog sync)
- Enterprise: Unlimited

### Conversations

View all conversations between your visitors and the AI assistant:

- **Message History**: Read the full back-and-forth between the visitor and the chatbot.
- **Visitor Identity**: See the visitor's session ID and optional display name.
- **Status Tracking**: Conversations are either "active" (ongoing) or "ended".
- **Satisfaction Scores**: Visitors can rate their experience from 1 to 5 stars. You can see these ratings on each conversation and in aggregate on the analytics page.

### Widget Customization

The chat widget embeds on your website with a single code snippet:

```html
<script src="https://shopchat.example.com/widget.js" data-widget-key="wk_YOUR_KEY_HERE"></script>
```

No framework dependency is required -- the widget works on any website (Shopify, WordPress, custom HTML, etc.).

**Customization options:**
- Widget colors match your store branding via theme_config
- Position: bottom-right or bottom-left of the screen
- Size: small, medium, or large
- White-label: Enterprise tier removes ShopChat branding entirely

### Analytics

The Analytics page shows you how your chatbots are performing:

- **Total Conversations**: How many chats have happened across all your chatbots.
- **Total Messages**: The total number of messages exchanged.
- **Average Satisfaction**: The average star rating across rated conversations.
- **Active Chatbots**: How many chatbots are currently enabled.
- **Conversations Today**: Today's chat volume.
- **Top Chatbot**: Your most-used chatbot by conversation count.
- **Per-Chatbot Breakdown**: Detailed stats for each individual chatbot.

---

## Subscription Tiers

| Feature | Free | Pro ($19/mo) | Enterprise ($79/mo) |
|---------|------|-------------|-------------------|
| Monthly conversations | 50 | 1,000 | Unlimited |
| Knowledge base pages | 10 | 500 | Unlimited |
| Customization | Branding only | Personality + flows | White-label |
| Analytics | Basic | Full | Full + export + webhooks |
| API access | No | Yes | Yes |
| Trial | -- | 14 days free | 14 days free |

**What happens when you hit a limit?**
- **Conversation limit**: New visitors will not be able to start conversations until the next billing period. Existing active conversations continue working.
- **Knowledge base limit**: You will not be able to add new entries until you upgrade or delete existing entries.

---

## Getting Started

### Step 1: Create Your Account

1. Go to the ShopChat dashboard at `http://localhost:3108` (or your production URL).
2. Click **Register** and enter your email and password.
3. You start on the **Free** plan with 50 conversations/month and 10 knowledge base pages.

### Step 2: Create a Chatbot

1. Navigate to **Chatbots** in the sidebar.
2. Click **Create Chatbot**.
3. Fill in:
   - **Name**: e.g., "My Store Assistant"
   - **Personality**: e.g., "friendly"
   - **Welcome Message**: e.g., "Welcome to our store! How can I help you today?"
4. Optionally configure the theme colors.
5. Click **Save**. Your chatbot is created with a unique widget key.

### Step 3: Build Your Knowledge Base

1. Navigate to **Knowledge Base** in the sidebar.
2. Click **Add Entry**.
3. Select the chatbot this entry belongs to.
4. Choose a source type:
   - `product_catalog` for products (include price and URL in metadata)
   - `policy_page` for store policies
   - `faq` for frequently asked questions
   - `custom_text` for any other information
5. Enter a title and the full content.
6. Click **Save**.
7. Repeat for all the information you want the chatbot to know.

### Step 4: Embed the Widget

1. Navigate to **Chatbots** and find your chatbot's **widget key** (it starts with `wk_`).
2. Add the widget script to your website's HTML:
   ```html
   <script src="https://shopchat.example.com/widget.js" data-widget-key="wk_YOUR_KEY_HERE"></script>
   ```
3. The chat bubble will appear on your store, ready for visitors to use.

### Step 5: Monitor and Improve

1. Navigate to **Conversations** to review chat history and see what customers are asking.
2. Check the **Analytics** page to track satisfaction scores and conversation volume.
3. Update your knowledge base regularly with new products, updated policies, and answers to common questions.
4. Adjust your chatbot's personality and welcome message based on feedback.

### Step 6: Upgrade When Ready

1. Navigate to **Billing** in the sidebar.
2. Review the available plans.
3. Click **Upgrade** on the plan that fits your needs.
4. Complete the checkout process. Your limits are updated immediately.

---

## Tips for Better Chatbot Performance

- **Be specific in your knowledge base**: The more detailed your entries, the better the AI can answer. Instead of "We ship fast", write "Standard shipping takes 3-5 business days. Free shipping on orders over $50."
- **Add product catalog entries with metadata**: Include the product price and URL in the metadata field so the chatbot can show product suggestions with direct links.
- **Use descriptive titles**: The AI searches titles and content for matching keywords. "Return Policy - 30 Day Guarantee" is better than just "Returns".
- **Review conversations regularly**: See what customers are asking and add knowledge base entries for questions the chatbot could not answer well.
- **Keep your knowledge base current**: Update product information, prices, and policies when they change.
