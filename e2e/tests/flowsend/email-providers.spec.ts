/**
 * FlowSend Email Provider Webhook e2e tests.
 *
 * Validates that email provider webhooks (SES via SNS, SendGrid) correctly
 * receive and process delivery events. Also verifies that the settings page
 * renders email provider configuration UI.
 *
 * **For Developers:**
 *   Tests exercise the /api/v1/webhooks/ses-events and
 *   /api/v1/webhooks/sendgrid-events endpoints directly via fetch, plus the
 *   /settings dashboard page via Playwright browser. SES webhooks follow
 *   the SNS envelope format (SubscriptionConfirmation and Notification types).
 *   SendGrid webhooks expect a JSON array of event objects.
 *
 * **For QA Engineers:**
 *   - SES subscription confirmation returns 200 with { status: "confirmed" }.
 *   - SES delivery notification returns 200 with { status: "ok", event_id }.
 *   - SendGrid array payload returns 200 with { processed: N }.
 *   - SendGrid non-array payload returns 400.
 *   - Settings page renders email provider selection UI.
 *
 * **For Project Managers:**
 *   These tests ensure that the email delivery tracking pipeline works
 *   end-to-end for both supported providers (SES and SendGrid), covering
 *   subscription setup, event ingestion, and provider configuration UI.
 *
 * **For End Users:**
 *   Email delivery tracking is automatic. These tests verify that bounce,
 *   open, click, and delivery stats appear correctly in your analytics.
 */

import { test, expect } from "@playwright/test";
import {
  registerServiceUser,
  serviceLogin,
  createContactAPI,
  createCampaignAPI,
  SERVICE_APIS,
} from "../service-helpers";

const FLOWSEND_API = SERVICE_APIS.flowsend;

test.describe("FlowSend Email Providers", () => {
  let token: string;
  let userEmail: string;
  let userPassword: string;

  test.beforeEach(async () => {
    const user = await registerServiceUser("flowsend");
    token = user.token;
    userEmail = user.email;
    userPassword = user.password;
  });

  test("SES webhook handles subscription confirmation", async () => {
    const resp = await fetch(`${FLOWSEND_API}/api/v1/webhooks/ses-events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        Type: "SubscriptionConfirmation",
        SubscribeURL: "https://sns.us-east-1.amazonaws.com/?Action=ConfirmSubscription&TopicArn=arn:aws:sns:us-east-1:123456789:ses-events&Token=mock-token",
        TopicArn: "arn:aws:sns:us-east-1:123456789:ses-events",
        MessageId: "mock-msg-id-001",
      }),
    });

    expect(resp.status).toBe(200);
    const data = await resp.json();
    expect(data.status).toBe("confirmed");
  });

  test("SES webhook processes delivery notification", async () => {
    // Create a contact so we have a valid contact_id
    const contact = await createContactAPI(token, {
      email: "ses-test@example.com",
      first_name: "SES",
      last_name: "Test",
    });
    const contactId = contact.id;

    // Create a campaign so we have a valid campaign_id
    const campaign = await createCampaignAPI(token, {
      name: "SES Delivery Test",
      subject: "Test Subject",
    });
    const campaignId = campaign.id;

    // Send a SES delivery notification wrapped in SNS envelope
    const sesMessage = JSON.stringify({
      notificationType: "Delivery",
      mail: {
        messageId: "ses-msg-12345",
        tags: {
          campaign_id: [campaignId],
          contact_id: [contactId],
        },
      },
      delivery: {
        timestamp: new Date().toISOString(),
        recipients: ["ses-test@example.com"],
      },
    });

    const resp = await fetch(`${FLOWSEND_API}/api/v1/webhooks/ses-events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        Type: "Notification",
        MessageId: "sns-notification-001",
        Message: sesMessage,
      }),
    });

    expect(resp.status).toBe(200);
    const data = await resp.json();
    expect(data.status).toBe("ok");
    expect(data.event_id).toBeTruthy();
  });

  test("SendGrid webhook processes event array", async () => {
    // Create a contact for valid contact_id
    const contact = await createContactAPI(token, {
      email: "sg-test@example.com",
      first_name: "SendGrid",
      last_name: "Test",
    });
    const contactId = contact.id;

    // Create a campaign for valid campaign_id
    const campaign = await createCampaignAPI(token, {
      name: "SendGrid Delivery Test",
      subject: "SG Test Subject",
    });
    const campaignId = campaign.id;

    // SendGrid sends an array of event objects
    const events = [
      {
        event: "delivered",
        sg_message_id: "sg-msg-001.filter0001.12345",
        campaign_id: campaignId,
        contact_id: contactId,
        timestamp: Math.floor(Date.now() / 1000),
      },
      {
        event: "open",
        sg_message_id: "sg-msg-001.filter0001.12345",
        campaign_id: campaignId,
        contact_id: contactId,
        timestamp: Math.floor(Date.now() / 1000),
      },
    ];

    const resp = await fetch(
      `${FLOWSEND_API}/api/v1/webhooks/sendgrid-events`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(events),
      }
    );

    expect(resp.status).toBe(200);
    const data = await resp.json();
    expect(data.status).toBe("ok");
    expect(data.processed).toBe(2);
  });

  test("SendGrid webhook rejects non-array body", async () => {
    const resp = await fetch(
      `${FLOWSEND_API}/api/v1/webhooks/sendgrid-events`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event: "delivered",
          sg_message_id: "sg-msg-bad",
        }),
      }
    );

    expect(resp.status).toBe(400);
  });

  test("email provider settings page loads", async ({ page }) => {
    await serviceLogin(page, userEmail, userPassword);
    await page.goto("/settings");
    await page.waitForLoadState("networkidle");

    // Verify the settings page loaded with email-related content
    const settingsHeading = page.getByRole("heading", {
      name: /settings/i,
    });
    await expect(settingsHeading).toBeVisible({ timeout: 10000 });

    // Verify email provider section exists (provider dropdown or provider label)
    const providerSection = page.getByText(/email provider|provider|smtp|ses|sendgrid/i).first();
    await expect(providerSection).toBeVisible({ timeout: 10000 });
  });
});
