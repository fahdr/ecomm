# FlowSend Phase 3 Features Documentation

This document covers two new capabilities added to FlowSend in Phase 3: **Email API Integration (SES + SendGrid)** and **SMS Marketing (Twilio + SNS)**. Each feature is documented for four audiences: Developer, Project Manager, QA Engineer, and End User.

---

## Table of Contents

- [Feature 2: Email API Integration (SES + SendGrid)](#feature-2-email-api-integration-ses--sendgrid)
  - [Developer](#email-api---developer)
  - [Project Manager](#email-api---project-manager)
  - [QA Engineer](#email-api---qa-engineer)
  - [End User](#email-api---end-user)
- [Feature 3: SMS Marketing (Twilio + SNS)](#feature-3-sms-marketing-twilio--sns)
  - [Developer](#sms-marketing---developer)
  - [Project Manager](#sms-marketing---project-manager)
  - [QA Engineer](#sms-marketing---qa-engineer)
  - [End User](#sms-marketing---end-user)

---

## Feature 2: Email API Integration (SES + SendGrid)

Extends FlowSend's email delivery layer from console/SMTP-only to four pluggable providers: Console, SMTP, AWS SES, and SendGrid. Adds webhook ingestion endpoints for real-time delivery tracking from SES and SendGrid.

---

### Email API -- Developer

#### Architecture

The email delivery system uses an abstract factory pattern. All senders implement the `AbstractEmailSender` interface defined in `app/services/email_sender.py`. The factory function `get_email_sender()` reads the `email_sender_mode` setting and returns the appropriate implementation via lazy imports to avoid requiring optional dependencies at startup.

```
AbstractEmailSender (ABC)
  |-- ConsoleEmailSender     (logs to stdout, default)
  |-- SmtpEmailSender         (aiosmtplib, existing)
  |-- SesEmailSender          (aioboto3, new)
  |-- SendGridEmailSender     (sendgrid SDK, new)
```

#### Key Files

| File | Purpose |
|------|---------|
| `backend/app/services/email_sender.py` | Abstract base class, Console/SMTP senders, `get_email_sender()` factory |
| `backend/app/services/ses_email_sender.py` | `SesEmailSender` -- AWS SES via aioboto3 `send_raw_email` |
| `backend/app/services/sendgrid_email_sender.py` | `SendGridEmailSender` -- SendGrid v3 API via official SDK |
| `backend/app/services/webhook_event_service.py` | `process_ses_event()` and `process_sendgrid_event()` functions |
| `backend/app/api/webhooks.py` | Webhook HTTP endpoints for SES and SendGrid delivery events |
| `backend/app/models/campaign.py` | `EmailEvent` model with `provider_message_id` and `error_code` fields |
| `backend/app/config.py` | Settings: `email_sender_mode`, SES credentials, SendGrid API key |
| `dashboard/src/app/settings/page.tsx` | Settings UI with email provider card selector and credential forms |
| `backend/tests/test_email_providers.py` | 29 backend tests covering senders, webhooks, and endpoints |

#### API Contracts

**Factory Function**

```python
def get_email_sender() -> AbstractEmailSender:
    """Returns sender based on settings.email_sender_mode: 'console' | 'smtp' | 'ses' | 'sendgrid'."""
```

**Sender Interface**

```python
async def send(self, to: str, subject: str, html_body: str, plain_body: str | None = None) -> bool:
    """Send one email. Returns True on success, False on failure."""
```

**SES Sender Implementation Details**

- Uses `aioboto3.Session` with explicit credentials (`ses_access_key_id`, `ses_secret_access_key`, `ses_region`).
- Constructs a MIME multipart/alternative message for full MIME control.
- Calls `send_raw_email` with optional `ConfigurationSetName` for SES event tracking.
- Falls back to False on any exception; logs the stack trace.

**SendGrid Sender Implementation Details**

- Uses the `sendgrid.SendGridAPIClient` with `sendgrid_api_key`.
- Constructs a `Mail` object via `sendgrid.helpers.mail`.
- The SDK call is synchronous but wrapped in the async interface for pattern consistency.
- Accepts status codes 200, 201, 202 as success.

**Webhook Endpoints**

| Method | Path | Content-Type | Description |
|--------|------|--------------|-------------|
| `POST` | `/api/v1/webhooks/ses-events` | `application/json` | Receives SES notifications via SNS. Handles `SubscriptionConfirmation` and `Notification` types. |
| `POST` | `/api/v1/webhooks/sendgrid-events` | `application/json` | Receives SendGrid Event Webhook callbacks as a JSON array of event objects. |

**SES Event Mapping** (SNS notification `notificationType` to internal `event_type`):

| SES Type | Internal Type |
|----------|---------------|
| `Bounce` | `bounced` |
| `Complaint` | `bounced` |
| `Delivery` | `delivered` |
| `Open` | `opened` |
| `Click` | `clicked` |

**SendGrid Event Mapping** (webhook `event` field to internal `event_type`):

| SendGrid Event | Internal Type |
|----------------|---------------|
| `delivered` | `delivered` |
| `bounce` | `bounced` |
| `open` | `opened` |
| `click` | `clicked` |
| `unsubscribe` | `unsubscribed` |

**Webhook Event Service Functions**

```python
async def process_ses_event(db: AsyncSession, event_data: dict) -> EmailEvent | None:
    """Parse SES SNS notification, map to internal type, create EmailEvent.
    Returns None for unknown types or missing contact_id.
    Stores bounce.bounceType or complaint.complaintFeedbackType as error_code."""

async def process_sendgrid_event(db: AsyncSession, event_data: dict) -> EmailEvent | None:
    """Parse SendGrid event, map to internal type, create EmailEvent.
    Returns None for unknown types or missing contact_id.
    Stores bounce reason as error_code."""
```

**EmailEvent Model Extensions**

Two new nullable columns added to the `email_events` table:

| Column | Type | Purpose |
|--------|------|---------|
| `provider_message_id` | `String(255)` | SES `messageId` or SendGrid `sg_message_id` |
| `error_code` | `String(100)` | SES `bounceType`/`complaintFeedbackType` or SendGrid `reason` |

**Configuration Settings** (in `app/config.py`):

```python
email_sender_mode: str = "console"  # "console", "smtp", "ses", "sendgrid"
ses_region: str = "us-east-1"
ses_access_key_id: str = ""
ses_secret_access_key: str = ""
ses_configuration_set: str = ""
sendgrid_api_key: str = ""
```

#### Dashboard Integration

The Settings page (`dashboard/src/app/settings/page.tsx`) adds an "Email Provider" card with:

- A 4-card selector grid: Console, SMTP, AWS SES, SendGrid.
- Conditional credential fields per provider:
  - **Console**: Informational text only, no fields.
  - **SMTP**: Host, Port, Username, Password, From Address, From Name, TLS toggle.
  - **SES**: Region, Access Key ID, Secret Access Key, Configuration Set (optional).
  - **SendGrid**: API Key (password field).
- Save button calls `POST /api/v1/settings/email-provider` with provider-specific payload.
- Toast notifications on save success/failure.

---

### Email API -- Project Manager

#### Feature Scope

This feature extends FlowSend from a single-provider email system (console + SMTP) to a multi-provider platform supporting enterprise-grade email delivery via AWS SES and SendGrid. Merchants can now choose the provider that best fits their scale, budget, and deliverability requirements.

#### Business Value

- **SES**: Lowest-cost option for high-volume senders ($0.10 per 1,000 emails). Ideal for merchants sending 100K+ emails/month.
- **SendGrid**: Built-in bounce handling, compliance features, and analytics. Preferred by merchants who want managed deliverability.
- **Webhook tracking**: Real-time bounce, open, click, and complaint events enable campaign analytics dashboards and contact engagement scoring.

#### Dependencies

- **External packages**: `aioboto3` (SES), `sendgrid` (SendGrid SDK). Both are lazily imported -- no impact on startup if unused.
- **AWS setup**: SES requires verified sender domains in the AWS console and an SNS topic subscribed to this webhook endpoint.
- **SendGrid setup**: Requires a SendGrid API key with Mail Send permissions and Event Webhook configured in the SendGrid dashboard.

#### Progress Milestones

| Milestone | Status |
|-----------|--------|
| Abstract sender pattern with factory | Complete |
| SES sender implementation (`ses_email_sender.py`) | Complete |
| SendGrid sender implementation (`sendgrid_email_sender.py`) | Complete |
| Factory updated for 4 modes (console, smtp, ses, sendgrid) | Complete |
| Webhook event service (`webhook_event_service.py`) | Complete |
| SES webhook endpoint (`POST /webhooks/ses-events`) | Complete |
| SendGrid webhook endpoint (`POST /webhooks/sendgrid-events`) | Complete |
| EmailEvent model extended with `provider_message_id`, `error_code` | Complete |
| Dashboard Settings page with provider selector | Complete |
| Backend tests (29 tests in `test_email_providers.py`) | Complete |
| E2E tests (5 tests in `email-providers.spec.ts`) | Complete |

#### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| AWS credentials misconfigured | SES sender catches all exceptions, returns False, and logs the error. Console mode is the safe default. |
| SendGrid API key leaked | Dashboard uses `type="password"` for the API key field. Settings are stored server-side, not exposed to the frontend after save. |
| Webhook replay attacks | SES webhooks could be validated via SNS signature verification (future enhancement). SendGrid supports signed Event Webhooks. |

---

### Email API -- QA Engineer

#### Test Coverage Summary

- **Backend unit/integration tests**: 29 tests in `backend/tests/test_email_providers.py`
- **E2E tests**: 5 tests in `e2e/tests/flowsend/email-providers.spec.ts`

#### Test Plan

**1. Sender Factory Tests**

| Test Case | Expected Result |
|-----------|-----------------|
| `email_sender_mode="console"` | `get_email_sender()` returns `ConsoleEmailSender` |
| `email_sender_mode="smtp"` | `get_email_sender()` returns `SmtpEmailSender` |
| `email_sender_mode="ses"` | `get_email_sender()` returns `SesEmailSender` |
| `email_sender_mode="sendgrid"` | `get_email_sender()` returns `SendGridEmailSender` |

**2. Console Sender Tests**

| Test Case | Expected Result |
|-----------|-----------------|
| `ConsoleEmailSender.send()` | Returns `True`, logs message details to stdout |

**3. SES Sender Initialization**

| Test Case | Expected Result |
|-----------|-----------------|
| Default construction | Reads `ses_region`, `ses_access_key_id`, `ses_secret_access_key` from settings |
| Explicit parameters | Uses provided values over settings |

**4. SendGrid Sender Initialization**

| Test Case | Expected Result |
|-----------|-----------------|
| Default construction | Reads `sendgrid_api_key`, `email_from_address`, `email_from_name` from settings |

**5. SES Webhook Event Processing**

| Test Case | Expected Result |
|-----------|-----------------|
| Bounce notification | Creates `EmailEvent` with `event_type="bounced"`, stores `bounceType` as `error_code` |
| Complaint notification | Creates `EmailEvent` with `event_type="bounced"`, stores `complaintFeedbackType` as `error_code` |
| Delivery notification | Creates `EmailEvent` with `event_type="delivered"` |
| Open notification | Creates `EmailEvent` with `event_type="opened"` |
| Click notification | Creates `EmailEvent` with `event_type="clicked"` |
| Unknown notification type | Returns `None`, no record created |
| Missing contact_id in tags | Returns `None`, no record created |

**6. SendGrid Webhook Event Processing**

| Test Case | Expected Result |
|-----------|-----------------|
| `delivered` event | Creates `EmailEvent` with `event_type="delivered"` |
| `bounce` event | Creates `EmailEvent` with `event_type="bounced"` |
| `open` event | Creates `EmailEvent` with `event_type="opened"` |
| `click` event | Creates `EmailEvent` with `event_type="clicked"` |
| `unsubscribe` event | Creates `EmailEvent` with `event_type="unsubscribed"` |
| Unknown event type (e.g., `dropped`) | Returns `None`, no record created |
| Missing contact_id | Returns `None`, no record created |
| Bounce with reason | Stores `reason` as `error_code` |

**7. Webhook API Endpoint Tests**

| Test Case | Expected Result |
|-----------|-----------------|
| SES: SNS SubscriptionConfirmation | Returns 200 with `{"status": "confirmed"}` |
| SES: Valid Notification with Delivery event | Returns 200 with `event_id` in response |
| SES: Malformed JSON body | Returns 400 |
| SendGrid: Valid event array (2 events) | Returns 200, `processed: 2` |
| SendGrid: Empty array | Returns 200, `processed: 0` |
| SendGrid: Non-array body | Returns 400 |

**8. Dashboard Settings E2E Tests**

| Test Case | Expected Result |
|-----------|-----------------|
| Select Console provider | No credential fields shown, info message displayed |
| Select SMTP provider | Shows host, port, username, password, from address, from name, TLS toggle |
| Select SES provider | Shows region, access key ID, secret access key, configuration set fields |
| Select SendGrid provider | Shows API key field (password masked) |
| Save with valid credentials | Toast shows "Email provider settings saved." |

#### Edge Cases

- SES event with `notificationType` present but empty string: returns `None`.
- SendGrid event array containing a mix of valid and invalid events: valid events are processed, invalid ones are logged and skipped without aborting the batch.
- UUID parsing: invalid UUID strings in `contact_id` or `campaign_id` fields are handled gracefully (returns `None` via `_parse_uuid`).
- SES notification with tags containing multiple campaign_ids: only the first element is used.

#### Acceptance Criteria

1. The `get_email_sender()` factory returns the correct sender class for each of the four modes.
2. SES and SendGrid senders return `True` on successful send and `False` on any failure.
3. Webhook endpoints correctly map all documented provider event types to internal `EmailEvent` records.
4. `provider_message_id` and `error_code` are populated on relevant events.
5. The dashboard Settings page shows the correct credential fields for each selected provider.
6. All 29 backend tests pass. All 5 E2E tests pass.

---

### Email API -- End User

#### Overview

FlowSend now supports three email delivery providers in addition to the default development mode. You can configure your preferred provider from the Settings page in the dashboard.

#### Available Providers

| Provider | Best For | Cost |
|----------|----------|------|
| **Console** | Local development and testing. Emails are logged but not delivered. | Free |
| **SMTP** | Custom mail servers (Mailgun, Postmark, etc.) | Varies by SMTP provider |
| **AWS SES** | High-volume senders who want the lowest per-email cost. | ~$0.10 per 1,000 emails |
| **SendGrid** | Merchants who want managed deliverability with built-in analytics. | Free tier available, paid plans from $19.95/mo |

#### How to Configure Your Email Provider

1. Navigate to **Settings** in the sidebar.
2. In the **Email Provider** card, click on the provider you want to use.
3. Fill in the required credentials:
   - **SMTP**: Server host, port, username, password, from address, display name, and TLS preference.
   - **AWS SES**: AWS region, Access Key ID, Secret Access Key, and optional Configuration Set name.
   - **SendGrid**: Your SendGrid API key (create one in the SendGrid dashboard with Mail Send permissions).
4. Click **Save Email Settings**.
5. A success toast confirms your settings are saved.

#### Delivery Tracking

Once configured, FlowSend automatically tracks email delivery events from your provider:

- **Delivered**: Your email reached the recipient's inbox.
- **Bounced**: The email could not be delivered (invalid address, full mailbox, etc.).
- **Opened**: The recipient opened your email.
- **Clicked**: The recipient clicked a link in your email.

These events appear in your campaign analytics dashboard in real-time. No manual setup is needed -- delivery tracking webhooks are configured automatically when you select a provider.

#### Switching Providers

You can switch providers at any time from the Settings page. The new provider takes effect immediately for all future campaign sends. Historical delivery data from your previous provider is preserved in your analytics.

---

## Feature 3: SMS Marketing (Twilio + SNS)

Adds a complete SMS marketing channel to FlowSend: SMS campaigns, reusable templates, delivery tracking, and webhook ingestion from Twilio and AWS SNS. Includes three new dashboard pages and sidebar navigation updates.

---

### SMS Marketing -- Developer

#### Architecture

SMS delivery mirrors the email sender pattern with its own abstract base class and factory function. The SMS feature introduces new models, a dedicated service layer, API router, and three dashboard pages.

```
AbstractSmsSender (ABC)
  |-- ConsoleSmsSender        (logs to stdout, default)
  |-- TwilioSmsSender          (Twilio REST API)
  |-- AwsSnsSmsSender          (AWS SNS publish)
```

#### Key Files

| File | Purpose |
|------|---------|
| **Backend: Sender Layer** | |
| `backend/app/services/sms_sender.py` | Abstract base class, `ConsoleSmsSender`, `get_sms_sender()` factory |
| `backend/app/services/twilio_sms_sender.py` | `TwilioSmsSender` -- Twilio REST API via official SDK |
| `backend/app/services/sns_sms_sender.py` | `AwsSnsSmsSender` -- AWS SNS `publish` for direct SMS |
| **Backend: Models** | |
| `backend/app/models/sms_template.py` | `SmsTemplate` model (name, body, category) |
| `backend/app/models/sms_event.py` | `SmsEvent` model (campaign_id, contact_id, event_type, provider_message_id, error_code) |
| `backend/app/models/campaign.py` | `Campaign` model extended with `channel`, `sms_body` fields |
| `backend/app/models/contact.py` | `Contact` model extended with `phone_number`, `sms_subscribed`, `sms_unsubscribed_at` |
| **Backend: Service** | |
| `backend/app/services/sms_campaign_service.py` | Campaign CRUD, send orchestration, analytics aggregation |
| **Backend: API** | |
| `backend/app/api/sms.py` | SMS campaigns and templates CRUD endpoints |
| `backend/app/api/webhooks.py` | Twilio and SNS SMS delivery webhook endpoints |
| `backend/app/schemas/sms.py` | Pydantic request/response schemas |
| `backend/app/config.py` | SMS provider settings (Twilio, SNS credentials) |
| **Dashboard** | |
| `dashboard/src/app/sms/page.tsx` | SMS campaigns listing with KPI cards, table, send action |
| `dashboard/src/app/sms/new/page.tsx` | Create new SMS campaign with character/segment counters |
| `dashboard/src/app/sms/templates/page.tsx` | SMS templates grid with create/edit/delete dialogs |
| `dashboard/src/app/settings/page.tsx` | Settings page with SMS provider selection |
| `dashboard/src/components/sidebar.tsx` | Updated sidebar with SMS nav entries + longest-prefix matching |
| `dashboard/src/service.config.ts` | Navigation config with `SMS Campaigns` and `SMS Templates` entries |
| **Tests** | |
| `backend/tests/test_sms.py` | 39 backend tests |
| `e2e/tests/flowsend/sms.spec.ts` | 8 E2E tests |

#### API Contracts

**SMS Sender Interface**

```python
class AbstractSmsSender(ABC):
    @abstractmethod
    async def send(self, to: str, body: str, from_number: str = "") -> bool:
        """Send one SMS. to: E.164 format. Returns True on success."""
```

**SMS Sender Factory**

```python
def get_sms_sender() -> AbstractSmsSender:
    """Returns sender based on settings.sms_provider_mode: 'console' | 'twilio' | 'sns'."""
```

**Provider Implementation Details**

- **TwilioSmsSender**: Uses `twilio.rest.Client` (synchronous SDK). Creates a message via `client.messages.create(body=, from_=, to=)`. Logs the message SID and status on success.
- **AwsSnsSmsSender**: Uses `aioboto3.Session` with explicit credentials. Calls `client.publish(PhoneNumber=to, Message=body)` with `SMSType=Transactional`. Does not require an SNS topic.

**SMS Campaign API Endpoints** (Router prefix: `/api/v1/sms`, all require JWT auth)

| Method | Path | Request Body | Response | Status |
|--------|------|-------------|----------|--------|
| `POST` | `/sms/campaigns` | `SmsCampaignCreate` | `SmsCampaignResponse` | 201 |
| `GET` | `/sms/campaigns?page=&page_size=` | -- | `list[SmsCampaignResponse]` | 200 |
| `GET` | `/sms/campaigns/{id}` | -- | `SmsCampaignResponse` | 200 / 404 |
| `POST` | `/sms/campaigns/{id}/send` | -- | `SmsCampaignResponse` | 200 / 404 |
| `GET` | `/sms/campaigns/{id}/analytics` | -- | Analytics dict | 200 / 404 |

**SMS Template API Endpoints** (Router prefix: `/api/v1/sms`, all require JWT auth)

| Method | Path | Request Body | Response | Status |
|--------|------|-------------|----------|--------|
| `POST` | `/sms/templates` | `SmsTemplateCreate` | `SmsTemplateResponse` | 201 |
| `GET` | `/sms/templates` | -- | `list[SmsTemplateResponse]` | 200 |
| `GET` | `/sms/templates/{id}` | -- | `SmsTemplateResponse` | 200 / 404 |
| `PATCH` | `/sms/templates/{id}` | `SmsTemplateUpdate` | `SmsTemplateResponse` | 200 / 404 |
| `DELETE` | `/sms/templates/{id}` | -- | (empty) | 204 / 404 |

**SMS Webhook Endpoints** (no auth required, provider verifies via callback)

| Method | Path | Content-Type | Description |
|--------|------|--------------|-------------|
| `POST` | `/api/v1/webhooks/twilio-sms-status` | `application/x-www-form-urlencoded` | Twilio SMS status callbacks (form data with `MessageSid`, `MessageStatus`) |
| `POST` | `/api/v1/webhooks/sns-sms-status` | `application/json` | AWS SNS SMS delivery receipts via SNS HTTP subscription |

**Twilio Status Mapping**:

| Twilio Status | Internal Type |
|---------------|---------------|
| `delivered` | `delivered` |
| `undelivered` | `failed` |
| `failed` | `failed` |
| `sent` | `sent` |
| `queued` | `sent` |

**SNS Delivery Status Mapping**:

| SNS Status | Internal Type |
|------------|---------------|
| `SUCCESS` | `delivered` |
| `FAILURE` | `failed` |

**Pydantic Schemas**

```python
class SmsCampaignCreate(BaseModel):
    name: str          # min_length=1, max_length=255
    sms_body: str      # min_length=1, max_length=1600
    list_id: UUID | None = None
    scheduled_at: datetime | None = None

class SmsCampaignResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    channel: str       # always "sms"
    sms_body: str | None
    status: str        # draft, sending, sent, failed
    scheduled_at: datetime | None
    sent_at: datetime | None
    total_recipients: int
    sent_count: int
    created_at: datetime
    updated_at: datetime

class SmsTemplateCreate(BaseModel):
    name: str          # min_length=1, max_length=255
    body: str          # min_length=1, max_length=1600
    category: str = "promotional"  # max_length=50

class SmsTemplateUpdate(BaseModel):
    name: str | None
    body: str | None   # max_length=1600
    category: str | None

class SmsTemplateResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    body: str
    category: str
    created_at: datetime
    updated_at: datetime
```

**Database Models**

`sms_templates` table:

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `UUID` | PK, auto-generated |
| `user_id` | `UUID` | FK -> `users.id`, indexed, CASCADE delete |
| `name` | `String(255)` | NOT NULL |
| `body` | `Text` | NOT NULL |
| `category` | `String(50)` | NOT NULL, default `"promotional"` |
| `created_at` | `DateTime(tz)` | server_default=now() |
| `updated_at` | `DateTime(tz)` | server_default=now(), onupdate=now() |

`sms_events` table:

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `UUID` | PK, auto-generated |
| `campaign_id` | `UUID` | FK -> `campaigns.id`, nullable, indexed, CASCADE delete |
| `flow_id` | `UUID` | FK -> `flows.id`, nullable, indexed, CASCADE delete |
| `contact_id` | `UUID` | FK -> `contacts.id`, NOT NULL, indexed, CASCADE delete |
| `event_type` | `String(30)` | NOT NULL, indexed. Values: `sent`, `delivered`, `failed`, `opted_out` |
| `provider_message_id` | `String(255)` | nullable |
| `error_code` | `String(100)` | nullable |
| `metadata` | `JSON` | nullable, extra event data |
| `created_at` | `DateTime(tz)` | server_default=now() |

`campaigns` table extensions:

| Column | Type | Purpose |
|--------|------|---------|
| `channel` | `String(10)` | `"email"` (default) or `"sms"` |
| `sms_body` | `Text` | SMS message content, nullable |

`contacts` table extensions:

| Column | Type | Purpose |
|--------|------|---------|
| `phone_number` | `String(20)` | E.164 phone number, nullable, indexed |
| `sms_subscribed` | `Boolean` | SMS opt-in flag, default `False` |
| `sms_unsubscribed_at` | `DateTime(tz)` | SMS opt-out timestamp, nullable |

**Campaign Service Functions** (`sms_campaign_service.py`):

```python
async def create_sms_campaign(db, user_id, name, sms_body, list_id=None, scheduled_at=None) -> Campaign
async def get_sms_campaigns(db, user_id, page=1, page_size=20) -> list[Campaign]
async def get_sms_campaign(db, user_id, campaign_id) -> Campaign  # raises ValueError if not found
async def send_sms_campaign_mock(db, campaign) -> Campaign  # sends to sms_subscribed contacts
async def get_sms_campaign_analytics(db, user_id, campaign_id) -> dict
```

**Configuration Settings** (in `app/config.py`):

```python
sms_provider_mode: str = "console"      # "console", "twilio", "sns"
twilio_account_sid: str = ""
twilio_auth_token: str = ""
twilio_from_number: str = ""            # E.164 format
sns_region: str = "us-east-1"
sns_access_key_id: str = ""
sns_secret_access_key: str = ""
```

#### Sidebar Navigation

The sidebar (`dashboard/src/components/sidebar.tsx`) implements longest-prefix matching to correctly highlight nested routes. When the user visits `/sms/templates`, the "SMS Templates" entry is active (not "SMS Campaigns" at `/sms`). This is achieved by checking whether a more specific sibling navigation item matches the current pathname.

Navigation entries added to `service.config.ts`:

```typescript
{ label: "SMS Campaigns", href: "/sms", icon: "MessageSquare" },
{ label: "SMS Templates", href: "/sms/templates", icon: "MessageSquareText" },
```

---

### SMS Marketing -- Project Manager

#### Feature Scope

SMS Marketing adds a second communication channel alongside email, enabling merchants to reach customers directly on their mobile devices. The feature covers the full lifecycle: campaign creation, contact targeting, message delivery, template management, and delivery analytics.

#### Business Value

- **Higher engagement**: SMS has 98% open rates vs. 20-30% for email. Merchants can reach time-sensitive audiences (flash sales, order updates, appointment reminders).
- **Multi-channel marketing**: Merchants can coordinate email and SMS campaigns from a single platform.
- **Revenue expansion**: SMS adds a new billable dimension to FlowSend's pricing tiers.

#### Dependencies

| Dependency | Type | Purpose |
|------------|------|---------|
| `twilio` Python SDK | Optional, lazily imported | Twilio SMS sending |
| `aioboto3` | Optional, lazily imported | AWS SNS SMS sending |
| Twilio account | External service | Phone number provisioning, SMS delivery |
| AWS SNS | External service | Cost-effective SMS delivery in 200+ countries |
| Contact `phone_number` field | Database migration | New column on existing `contacts` table |
| Campaign `channel` / `sms_body` fields | Database migration | New columns on existing `campaigns` table |

#### Progress Milestones

| Milestone | Status |
|-----------|--------|
| Abstract SMS sender pattern with factory | Complete |
| Console SMS sender (development mode) | Complete |
| Twilio SMS sender implementation | Complete |
| AWS SNS SMS sender implementation | Complete |
| SmsTemplate model and database table | Complete |
| SmsEvent model and database table | Complete |
| Contact model extended (phone_number, sms_subscribed, sms_unsubscribed_at) | Complete |
| Campaign model extended (channel, sms_body) | Complete |
| SMS campaign service (CRUD + send + analytics) | Complete |
| SMS API router (campaigns + templates endpoints) | Complete |
| Twilio SMS webhook endpoint | Complete |
| SNS SMS webhook endpoint | Complete |
| Pydantic schemas for SMS | Complete |
| Dashboard: SMS Campaigns listing page (`/sms`) | Complete |
| Dashboard: Create SMS campaign page (`/sms/new`) | Complete |
| Dashboard: SMS Templates management page (`/sms/templates`) | Complete |
| Dashboard: Settings page SMS provider section | Complete |
| Sidebar navigation with SMS entries + prefix matching fix | Complete |
| Backend tests (39 tests in `test_sms.py`) | Complete |
| E2E tests (8 tests in `sms.spec.ts`) | Complete |

#### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Twilio credentials exposed | Dashboard uses `type="password"` for auth token. Settings stored server-side only. |
| SMS spam compliance (TCPA/GDPR) | `sms_subscribed` flag on Contact model enforces opt-in. `sms_unsubscribed_at` tracks opt-out. Send function filters by `sms_subscribed=True`. |
| High SMS costs from accidental bulk sends | Send action requires explicit confirmation dialog. Console mode is the default (no real delivery). |
| Character limit confusion | Dashboard shows real-time character counter and segment counter (160 chars per segment, up to 10 segments / 1600 chars). |

#### Future Enhancements

- Scheduled SMS sends with Celery task queue.
- SMS A/B testing (body variants).
- SMS flow triggers (e.g., abandoned cart SMS after 30 minutes).
- Per-plan SMS send limits.
- Two-way SMS conversations via Twilio webhooks.

---

### SMS Marketing -- QA Engineer

#### Test Coverage Summary

- **Backend unit/integration tests**: 39 tests in `backend/tests/test_sms.py`
- **E2E tests**: 8 tests in `e2e/tests/flowsend/sms.spec.ts`

#### Test Plan

**1. SMS Sender Factory Tests**

| Test Case | Expected Result |
|-----------|-----------------|
| `sms_provider_mode="console"` | `get_sms_sender()` returns `ConsoleSmsSender` |
| `sms_provider_mode="twilio"` | `get_sms_sender()` returns `TwilioSmsSender` |
| `sms_provider_mode="sns"` | `get_sms_sender()` returns `AwsSnsSmsSender` |

**2. Console SMS Sender**

| Test Case | Expected Result |
|-----------|-----------------|
| `ConsoleSmsSender.send(to, body)` | Returns `True`, logs message details |

**3. Twilio Sender Initialization**

| Test Case | Expected Result |
|-----------|-----------------|
| Default construction | Reads `twilio_account_sid`, `twilio_auth_token`, `twilio_from_number` from settings |

**4. SNS Sender Initialization**

| Test Case | Expected Result |
|-----------|-----------------|
| Default construction | Reads `sns_region`, `sns_access_key_id`, `sns_secret_access_key` from settings |

**5. SMS Campaign Service Tests**

| Test Case | Expected Result |
|-----------|-----------------|
| `create_sms_campaign()` | Creates campaign with `channel="sms"`, `status="draft"` |
| `get_sms_campaigns()` | Returns only SMS campaigns for the user, ordered by `created_at` desc |
| `get_sms_campaign()` with valid ID | Returns the campaign |
| `get_sms_campaign()` with invalid ID | Raises `ValueError` |
| `get_sms_campaign()` with wrong user | Raises `ValueError` |
| `send_sms_campaign_mock()` | Creates `SmsEvent` per contact, updates `sent_count`, sets `status="sent"` |
| `send_sms_campaign_mock()` skips contacts without phone | Only sends to contacts with `phone_number` set |
| `send_sms_campaign_mock()` respects `sms_subscribed` | Only sends to contacts with `sms_subscribed=True` |
| `get_sms_campaign_analytics()` | Returns aggregated event counts by type |

**6. SMS Campaign API Endpoint Tests**

| Test Case | Expected Result |
|-----------|-----------------|
| `POST /sms/campaigns` without auth | Returns 401 |
| `POST /sms/campaigns` with valid data | Returns 201 with `SmsCampaignResponse` |
| `GET /sms/campaigns` | Returns paginated list of SMS campaigns |
| `GET /sms/campaigns/{id}` for missing campaign | Returns 404 |
| `POST /sms/campaigns/{id}/send` for draft campaign | Returns 200, status changed to "sent" |
| `POST /sms/campaigns/{id}/send` for missing campaign | Returns 404 |

**7. SMS Template API Endpoint Tests**

| Test Case | Expected Result |
|-----------|-----------------|
| `POST /sms/templates` | Returns 201 with `SmsTemplateResponse` |
| `GET /sms/templates` | Returns list of templates |
| `GET /sms/templates/{id}` for existing template | Returns 200 with template data |
| `GET /sms/templates/{id}` for missing template | Returns 404 |
| `PATCH /sms/templates/{id}` with partial data | Returns 200, only specified fields updated |
| `DELETE /sms/templates/{id}` | Returns 204 (empty body) |
| `DELETE /sms/templates/{id}` for missing template | Returns 404 |

**8. SMS Webhook Endpoint Tests**

| Test Case | Expected Result |
|-----------|-----------------|
| Twilio: `MessageStatus=delivered` | Creates `SmsEvent` with `event_type="delivered"` |
| Twilio: `MessageStatus=failed` | Creates `SmsEvent` with `event_type="failed"` |
| Twilio: Missing `MessageSid` | Returns 400 |
| Twilio: Unknown status (e.g., `accepted`) | Returns 200 with `skipped: true` |
| SNS: SubscriptionConfirmation | Returns 200 with `status: "confirmed"` |
| SNS: Notification with `status=SUCCESS` | Creates `SmsEvent` with `event_type="delivered"` |
| SNS: Notification with `status=FAILURE` | Creates `SmsEvent` with `event_type="failed"` |
| SNS: Malformed JSON | Returns 400 |

**9. Dashboard E2E Tests**

| Test Case | Expected Result |
|-----------|-----------------|
| SMS Campaigns page loads | Shows page header "SMS Campaigns" and "New Campaign" button |
| Empty state | Shows "No SMS campaigns yet" with create link |
| Create new SMS campaign | Form validates name/body required, character counter works, redirects to `/sms` on success |
| SMS Templates page loads | Shows "SMS Templates" header and "New Template" button |
| Create template dialog | Opens with empty fields, validates required fields, character counter works |
| Edit template dialog | Pre-fills with existing template data |
| Delete template dialog | Shows confirmation, removes template from list on confirm |
| Settings SMS provider selection | Console/Twilio/SNS cards show correct credential fields |

#### Edge Cases

- SMS body at exactly 1600 characters: accepted (boundary test).
- SMS body at 1601 characters: rejected by Pydantic schema validation (`max_length=1600`).
- Empty SMS body: rejected by Pydantic schema validation (`min_length=1`).
- Campaign with `list_id=None`: sends to all SMS-subscribed contacts for the user.
- Contact with `sms_subscribed=True` but `phone_number=None`: skipped during send (no error).
- Twilio webhook with `contact_id` missing from form data: `SmsEvent` is not persisted (guard check on `sms_event.contact_id`).
- SNS webhook with unknown delivery status (not SUCCESS or FAILURE): returns `{"status": "ok", "skipped": true}`.
- Concurrent template delete and edit: delete wins (edit returns 404 after deletion).
- Pagination edge: requesting page beyond total pages returns empty list.

#### Acceptance Criteria

1. The `get_sms_sender()` factory returns the correct sender class for each of the three modes.
2. SMS campaigns are created with `channel="sms"` and only appear in SMS-specific queries.
3. The send function delivers messages only to contacts with `sms_subscribed=True` and a non-null `phone_number`.
4. An `SmsEvent` record is created for each successfully dispatched message.
5. Campaign analytics accurately aggregate `SmsEvent` counts by type.
6. All template CRUD operations work correctly with proper HTTP status codes (201, 200, 204, 404).
7. Twilio webhook processes form-encoded status callbacks and creates `SmsEvent` records.
8. SNS webhook handles SubscriptionConfirmation and delivery Notifications.
9. Dashboard SMS Campaigns page displays KPI cards, campaign table, status badges, and send action.
10. Dashboard Create Campaign page validates input, shows character/segment counters, and redirects on success.
11. Dashboard SMS Templates page supports grid display, create/edit/delete via dialogs.
12. Settings page SMS provider section shows correct credential fields per selected provider.
13. Sidebar highlights the correct SMS nav entry using longest-prefix matching.
14. All 39 backend tests pass. All 8 E2E tests pass.

---

### SMS Marketing -- End User

#### Overview

FlowSend now includes SMS Marketing, allowing you to send text message campaigns directly to your contacts' phones. You can create campaigns, manage reusable templates, and track delivery status -- all from the same dashboard you use for email marketing.

#### Getting Started

**Step 1: Configure Your SMS Provider**

1. Go to **Settings** in the sidebar.
2. Scroll to the **SMS Provider** card.
3. Choose your provider:
   - **Console** (default): For testing. Messages are logged but not delivered.
   - **Twilio**: Enter your Account SID, Auth Token, and From Number from the Twilio console.
   - **AWS SNS**: Enter your AWS Region, Access Key ID, and Secret Access Key.
4. Click **Save SMS Settings**.

**Step 2: Add Phone Numbers to Your Contacts**

Your contacts need phone numbers to receive SMS. When adding or editing contacts, include their phone number in E.164 format (e.g., `+15551234567`). Make sure the "SMS Subscribed" option is enabled for contacts who have opted in to receive text messages.

**Step 3: Create an SMS Campaign**

1. Click **SMS Campaigns** in the sidebar.
2. Click the **New Campaign** button.
3. Fill in the form:
   - **Campaign Name**: A descriptive name (e.g., "Flash Sale Alert").
   - **SMS Body**: Your message text. The character counter shows how many characters you have remaining (max 1,600) and how many SMS segments your message will use (1 segment = 160 characters).
   - **Contact List** (optional): Choose a specific list, or leave as "All contacts" to send to everyone who is SMS-subscribed.
   - **Schedule** (optional): Toggle the switch to schedule for a future date and time, or leave off to create a draft for immediate sending.
4. Click **Create Campaign** (or **Schedule Campaign** if scheduling).

**Step 4: Send Your Campaign**

1. On the **SMS Campaigns** page, find your draft campaign in the list.
2. Click the green **Send** button.
3. Confirm the send in the dialog that appears. This action cannot be undone.
4. Your campaign status changes to "sent" and delivery counts update.

#### SMS Campaigns Page

The campaigns page shows:

- **KPI Cards**: Total campaigns, sent count, draft count, and average delivery rate.
- **Campaign Table**: Each campaign shows its name, status badge (Draft, Sending, Sent, Scheduled), recipient count, sent count, and creation date.
- **Status Badges**: Color-coded for quick scanning -- green for sent, blue for sending, amber for scheduled, gray for draft.
- **Pagination**: Navigate through your campaigns with Previous/Next buttons.

#### SMS Templates

Templates let you save frequently used messages for quick reuse across campaigns.

1. Click **SMS Templates** in the sidebar.
2. Click **New Template** to create one:
   - **Name**: A descriptive name (e.g., "Welcome Message").
   - **Body**: Your reusable message text (max 1,600 characters).
   - **Category** (optional): Organize templates by type (e.g., "promotions", "alerts", "transactional").
3. Your templates appear in a grid view showing the name, category badge, body preview, character count, and creation date.
4. Hover over any template card to see **Edit** and **Delete** buttons.
5. Click **Edit** to update the template in a dialog, or **Delete** to remove it (with confirmation).

#### Delivery Tracking

FlowSend automatically tracks SMS delivery status from your provider:

- **Sent**: The message was dispatched to the carrier.
- **Delivered**: The carrier confirmed delivery to the recipient's phone.
- **Failed**: The message could not be delivered (invalid number, carrier rejection, etc.).

View delivery statistics in the campaign analytics view, accessible from each campaign's detail page.

#### SMS Best Practices

- **Keep messages short**: Aim for under 160 characters to fit in a single SMS segment. Longer messages work (up to 1,600 chars / 10 segments) but cost more.
- **Include a clear CTA**: Tell the recipient exactly what to do (e.g., "Reply STOP to unsubscribe" or "Shop now: https://...").
- **Respect opt-out**: Always honor unsubscribe requests. FlowSend tracks the `sms_subscribed` flag automatically.
- **Time your sends**: Avoid sending SMS late at night. Use the scheduling feature to send at optimal times.
- **Comply with regulations**: Ensure you have proper consent (TCPA in the US, GDPR in the EU) before sending marketing SMS.
