# FlowSend -- End User Guide

## What Is FlowSend?

FlowSend is your **Smart Email Marketing** platform. It helps you automate your email marketing with visual flow builders, broadcast campaigns, reusable templates, and detailed analytics. Whether you want to send a one-time newsletter or build a multi-step welcome sequence that runs on autopilot, FlowSend handles it all.

Use FlowSend to:
- **Grow your audience** by importing and managing email contacts
- **Automate engagement** with triggered email sequences (abandoned cart, welcome series, post-purchase follow-ups)
- **Send campaigns** like newsletters, promotions, and product announcements
- **Track performance** with delivery, open, click, and bounce analytics

---

## Features

### Contact Management

Contacts are the people you send emails to. FlowSend lets you:

- **Add contacts** one at a time or import them in bulk
- **Import contacts** by pasting a list of email addresses (comma, semicolon, or newline separated) or uploading CSV data with first name and last name columns
- **Organize with tags** -- add labels like "vip", "newsletter", or "beta" to segment your audience
- **Track subscription status** -- see who is subscribed and who has opted out
- **Create contact lists** -- group contacts into static lists (manually managed) or dynamic lists (automatically populated by rules like "all contacts with tag: premium")
- **Search and filter** -- find contacts quickly by email, name, or tag

### Automation Flows

Flows are automated email sequences that trigger based on subscriber actions. They are the core automation feature of FlowSend.

- **Trigger types**: Choose what starts the flow
  - **New Signup** -- when someone joins your list
  - **Purchase** -- when a customer buys something
  - **Abandoned Cart** -- when someone leaves items in their cart
  - **Scheduled** -- send at a specific time
  - **Custom Event** -- trigger from your own application events
- **Flow steps**: Define a sequence of actions (send email, wait, check conditions, branch)
- **Lifecycle management**: Flows start as drafts. When you are ready, activate them to start processing triggers. Pause anytime to stop without deleting.
  - **Draft** -- being built, not active
  - **Active** -- processing triggers and sending emails
  - **Paused** -- temporarily stopped, can be reactivated

### Broadcast Campaigns

Campaigns are one-time email sends to your contact list.

- **Create campaigns** with a name and subject line
- **Schedule for later** or save as draft and send when ready
- **Send to all subscribed contacts** -- unsubscribed contacts are automatically excluded
- **Track results** after sending:
  - How many emails were sent
  - How many were opened
  - How many links were clicked
  - How many bounced

### Email Templates

Templates are reusable email designs that speed up campaign creation.

- **System templates** -- pre-built designs ready to use (welcome, cart reminder, promo, newsletter, transactional)
- **Custom templates** -- create your own with HTML content and a text fallback
- **Categories** -- organize templates by type (welcome, cart, promo, newsletter, transactional)
- **Reuse** -- attach a template to any campaign or flow step

### Analytics

Track your email marketing performance across all campaigns and flows.

- **Aggregate metrics**: Total emails sent, opens, clicks, bounces across all campaigns
- **Per-campaign breakdown**: See how each individual campaign performed
- **Rates**: Open rate, click rate, and bounce rate as percentages
- **Contact engagement**: Understand which subscribers are most engaged

---

## Subscription Tiers

FlowSend offers three plans to match your needs:

| | Free | Pro | Enterprise |
|---|---|---|---|
| **Price** | $0/month | $39/month | $149/month |
| **Emails/month** | 500 | 25,000 | Unlimited |
| **Contacts** | 250 | 10,000 | Unlimited |
| **Automation Flows** | 2 | 20 | Unlimited |
| **Templates** | Basic | All | All |
| **A/B Testing** | -- | Yes | Yes |
| **API Access** | -- | Yes | Yes |
| **Dedicated IP** | -- | -- | Yes |
| **Free Trial** | -- | 14 days | 14 days |

You start on the Free plan automatically. Upgrade anytime from the Billing page in your dashboard.

---

## Getting Started

### Step 1: Register Your Account

1. Go to the FlowSend registration page
2. Enter your email address and choose a password (at least 8 characters)
3. Click **Register** -- you will be logged in automatically

### Step 2: Import Your Contacts

1. From the dashboard, click **Contacts** in the sidebar
2. Click the **Import** button in the top right
3. Paste your email addresses separated by commas, semicolons, or newlines
4. Optionally add tags (like "imported" or "newsletter") to all imported contacts
5. Click **Import Contacts**
6. FlowSend will tell you how many were imported and how many were skipped (duplicates)

You can also add contacts one at a time using the **Add Contact** button.

### Step 3: Create an Email Template

1. Click **Templates** in the sidebar
2. Browse the system templates or click **Create Template**
3. Give your template a name, subject line, and HTML content
4. Optionally add a plain-text fallback
5. Choose a category (welcome, promo, newsletter, etc.)
6. Save your template

### Step 4: Build an Automation Flow

1. Click **Flows** in the sidebar
2. Click **New Flow**
3. Give your flow a name (e.g., "Welcome Series")
4. Choose a trigger type (e.g., "New Signup")
5. Add your email steps -- each step specifies a template and a delay
6. Click **Create Flow** -- it will be saved as a draft
7. When you are ready, click **Activate** to start processing triggers

### Step 5: Send Your First Campaign

1. Click **Campaigns** in the sidebar
2. Click **New Campaign**
3. Enter a campaign name and email subject line
4. Optionally set a schedule date for future delivery
5. Click **Create Campaign** -- it will be saved as a draft
6. When you are ready, click **Send** and confirm
7. After sending, click **Analytics** to see how your campaign performed

---

## Dashboard Navigation

After logging in, your dashboard sidebar provides quick access to everything:

| Section | What It Does |
|---------|-------------|
| **Dashboard** | Overview of your plan, usage, and quick action buttons |
| **Flows** | Create and manage automated email sequences |
| **Campaigns** | Create, send, and track broadcast email campaigns |
| **Contacts** | Manage your subscriber list, import contacts, organize with tags |
| **Templates** | Browse system templates and create custom ones |
| **Analytics** | View aggregate email performance metrics |
| **API Keys** | Generate API keys for integrating FlowSend with your applications |
| **Billing** | View your current plan, upgrade, and manage your subscription |
| **Settings** | Account settings and preferences |

---

## Frequently Asked Questions

**Can I import contacts from another email marketing tool?**
Yes. Export your contacts as a CSV file with columns for email, first_name, and last_name, then use the Import feature on the Contacts page. FlowSend will automatically skip any duplicate email addresses.

**What happens when I reach my contact limit?**
New contact creation and imports will be rejected with an error message. Upgrade your plan to increase your limit.

**Can I edit a flow that is already active?**
No. Active flows must be paused first before you can edit them. This prevents accidental changes to running automations.

**What happens when I delete a contact?**
The contact is permanently removed along with their association to any lists and flows. This cannot be undone.

**How do I unsubscribe a contact?**
Edit the contact and toggle the "Subscribed" switch to off. Unsubscribed contacts will not receive any emails from campaigns or flows.

**Can I send a test email before a full campaign?**
The current version sends to all subscribed contacts. A/B testing and test sends are available on the Pro plan and above.

**How are my API keys secured?**
API keys are hashed with SHA-256 before storage. The raw key is only shown once when you create it. Store it securely -- it cannot be retrieved again.
