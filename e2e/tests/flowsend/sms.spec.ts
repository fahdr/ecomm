/**
 * FlowSend SMS Marketing e2e tests.
 *
 * Validates SMS campaign CRUD, SMS template management, campaign sending,
 * and SMS delivery status webhooks (Twilio, SNS). Tests cover both the
 * API layer and the dashboard UI for SMS features.
 *
 * **For Developers:**
 *   SMS endpoints are under /api/v1/sms/{campaigns,templates}. Campaign
 *   creation requires name + sms_body (max 1600 chars). Templates have
 *   name + body + category. Webhook endpoints for delivery status:
 *   /api/v1/webhooks/twilio-sms-status (form-encoded) and
 *   /api/v1/webhooks/sns-sms-status (JSON SNS envelope).
 *
 * **For QA Engineers:**
 *   - POST /sms/campaigns returns 201 with channel="sms"
 *   - GET /sms/campaigns returns paginated list
 *   - POST /sms/templates returns 201
 *   - POST /sms/campaigns/{id}/send transitions status to "sent"
 *   - Twilio form-encoded webhook returns 200
 *   - SNS SMS subscription confirmation returns confirmed
 *   - UI pages /sms and /sms/templates render correctly
 *
 * **For Project Managers:**
 *   These tests ensure the complete SMS marketing pipeline works:
 *   campaign creation, template management, sending, and delivery
 *   tracking through Twilio and SNS provider integrations.
 *
 * **For End Users:**
 *   Merchants can create SMS campaigns, use reusable templates, send
 *   messages to SMS-subscribed contacts, and track delivery status
 *   automatically via provider callbacks.
 */

import { test, expect } from "@playwright/test";
import {
  registerServiceUser,
  serviceLogin,
  serviceApiPost,
  serviceApiGet,
  createContactAPI,
  SERVICE_APIS,
} from "../service-helpers";

const FLOWSEND_API = SERVICE_APIS.flowsend;

test.describe("FlowSend SMS Marketing", () => {
  let token: string;
  let userEmail: string;
  let userPassword: string;

  test.beforeEach(async () => {
    const user = await registerServiceUser("flowsend");
    token = user.token;
    userEmail = user.email;
    userPassword = user.password;
  });

  test("SMS campaigns page loads with empty state", async ({ page }) => {
    await serviceLogin(page, userEmail, userPassword);
    await page.goto("/sms");
    await page.waitForLoadState("networkidle");

    // Verify SMS page heading or empty state is visible
    const heading = page.getByText(/sms|text message|campaigns/i).first();
    await expect(heading).toBeVisible({ timeout: 10000 });
  });

  test("can create SMS campaign via API", async () => {
    const campaign = await serviceApiPost("flowsend", token, "/api/v1/sms/campaigns", {
      name: "Flash Sale SMS",
      sms_body: "50% OFF today only! Shop now at example.com. Reply STOP to unsubscribe.",
    });

    expect(campaign).toBeTruthy();
    expect(campaign.name).toBe("Flash Sale SMS");
    expect(campaign.channel).toBe("sms");
    expect(campaign.sms_body).toContain("50% OFF");
    expect(campaign.status).toBe("draft");
    expect(campaign.id).toBeTruthy();
  });

  test("can list SMS campaigns via API", async () => {
    // Create two SMS campaigns
    await serviceApiPost("flowsend", token, "/api/v1/sms/campaigns", {
      name: "SMS Campaign Alpha",
      sms_body: "Alpha message content for testing.",
    });
    await serviceApiPost("flowsend", token, "/api/v1/sms/campaigns", {
      name: "SMS Campaign Beta",
      sms_body: "Beta message content for testing.",
    });

    // List all SMS campaigns
    const campaigns = await serviceApiGet(
      "flowsend",
      token,
      "/api/v1/sms/campaigns"
    );

    expect(Array.isArray(campaigns)).toBe(true);
    expect(campaigns.length).toBeGreaterThanOrEqual(2);

    const names = campaigns.map((c: { name: string }) => c.name);
    expect(names).toContain("SMS Campaign Alpha");
    expect(names).toContain("SMS Campaign Beta");
  });

  test("can create SMS template via API", async () => {
    const template = await serviceApiPost(
      "flowsend",
      token,
      "/api/v1/sms/templates",
      {
        name: "Order Confirmation SMS",
        body: "Hi {{first_name}}, your order #{{order_id}} has been confirmed! Track at {{tracking_url}}",
        category: "transactional",
      }
    );

    expect(template).toBeTruthy();
    expect(template.name).toBe("Order Confirmation SMS");
    expect(template.body).toContain("{{first_name}}");
    expect(template.category).toBe("transactional");
    expect(template.id).toBeTruthy();
  });

  test("SMS templates page loads", async ({ page }) => {
    await serviceLogin(page, userEmail, userPassword);

    // Create a template via API so the page has content
    await serviceApiPost("flowsend", token, "/api/v1/sms/templates", {
      name: "Welcome SMS Template",
      body: "Welcome to our store! Get 10% off your first order with code WELCOME10.",
      category: "promotional",
    });

    await page.goto("/sms/templates");
    await page.waitForLoadState("networkidle");

    // Verify the templates page loaded
    const pageContent = page.getByText(/template|sms/i).first();
    await expect(pageContent).toBeVisible({ timeout: 10000 });
  });

  test("can send SMS campaign via API", async () => {
    // Create an SMS-subscribed contact with phone number
    await createContactAPI(token, {
      email: "sms-subscriber@example.com",
      first_name: "SMS",
      last_name: "Subscriber",
      phone_number: "+15551234567",
      sms_subscribed: true,
    });

    // Create an SMS campaign
    const campaign = await serviceApiPost(
      "flowsend",
      token,
      "/api/v1/sms/campaigns",
      {
        name: "Send Test Campaign",
        sms_body: "This is a test SMS message for the send campaign test.",
      }
    );

    // Send the campaign
    const sent = await serviceApiPost(
      "flowsend",
      token,
      `/api/v1/sms/campaigns/${campaign.id}/send`,
      {}
    );

    expect(sent).toBeTruthy();
    expect(sent.status).toBe("sent");
  });

  test("Twilio webhook processes delivery status", async () => {
    // Create a contact so we have a valid contact_id to reference
    const contact = await createContactAPI(token, {
      email: "twilio-test@example.com",
      first_name: "Twilio",
      last_name: "Test",
      phone_number: "+15559876543",
      sms_subscribed: true,
    });

    // Post a Twilio form-encoded delivery status callback
    const resp = await fetch(
      `${FLOWSEND_API}/api/v1/webhooks/twilio-sms-status`,
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          MessageSid: "SM" + Date.now().toString(36) + "abc123",
          MessageStatus: "delivered",
          To: "+15559876543",
          From: "+15550001111",
          AccountSid: "AC_mock_account",
          ApiVersion: "2010-04-01",
        }).toString(),
      }
    );

    expect(resp.status).toBe(200);
    const data = await resp.json();
    expect(data.status).toBe("ok");
  });

  test("SNS SMS webhook handles subscription confirmation", async () => {
    const resp = await fetch(
      `${FLOWSEND_API}/api/v1/webhooks/sns-sms-status`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          Type: "SubscriptionConfirmation",
          SubscribeURL:
            "https://sns.us-east-1.amazonaws.com/?Action=ConfirmSubscription&TopicArn=arn:aws:sns:us-east-1:123456789:sms-status&Token=mock-token",
          TopicArn: "arn:aws:sns:us-east-1:123456789:sms-status",
          MessageId: "sns-sms-confirm-001",
        }),
      }
    );

    expect(resp.status).toBe(200);
    const data = await resp.json();
    expect(data.status).toBe("confirmed");
  });
});
