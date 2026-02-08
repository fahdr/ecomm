/**
 * Dashboard team and webhook management e2e tests.
 *
 * Tests team member invitation, listing, and webhook configuration.
 *
 * **For QA Engineers:**
 *   - Team page shows invited members with role and status.
 *   - Inviting a team member adds them to the list.
 *   - Webhook page shows configured endpoints with events.
 *   - Creating a webhook refreshes the list.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createStoreAPI,
  inviteTeamMemberAPI,
  createWebhookAPI,
} from "../helpers";

test.describe("Dashboard Team Management", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows team page", async ({ page }) => {
    await page.goto(`/stores/${storeId}/team`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/team|member|invite/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("lists invited members", async ({ page }) => {
    await inviteTeamMemberAPI(token, storeId, "alice@example.com");

    await page.goto(`/stores/${storeId}/team`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("alice@example.com")).toBeVisible({
      timeout: 10000,
    });
  });

  test("renders team member table with role and status", async ({ page }) => {
    await inviteTeamMemberAPI(token, storeId, "alice@team.com");
    await inviteTeamMemberAPI(token, storeId, "bob@team.com");

    await page.goto(`/stores/${storeId}/team`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("alice@team.com")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("bob@team.com")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("editor").first()).toBeVisible({ timeout: 10000 });
  });

  test("invites a team member via dialog", async ({ page }) => {
    await page.goto(`/stores/${storeId}/team`);
    await page.waitForLoadState("networkidle");
    // Wait for empty state to confirm page is loaded and interactive
    await expect(page.getByText(/no team member/i)).toBeVisible({ timeout: 10000 });

    // Use JS click to bypass React hydration timing issues
    await page.$eval('button:has-text("Invite your first member")', (el: HTMLElement) => el.click());
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5000 });

    await page.fill("#invite-email", "bob@example.com");

    // Click submit and wait for the POST to complete
    const [postResp] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes("/team") && resp.request().method() === "POST",
        { timeout: 10000 }
      ),
      page.locator('[role="dialog"] button[type="submit"]').click(),
    ]);

    // Wait for dialog to close
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 10000 });

    // Reload to ensure fresh data from the database
    await page.reload();
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("bob@example.com")).toBeVisible({
      timeout: 10000,
    });
  });
});

test.describe("Dashboard Webhook Management", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows empty webhook state", async ({ page }) => {
    await page.goto(`/stores/${storeId}/webhooks`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/no webhook|webhook/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("renders webhook table with URL and events", async ({ page }) => {
    await createWebhookAPI(token, storeId);

    await page.goto(`/stores/${storeId}/webhooks`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("hooks.example.com").first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("order.created").first()).toBeVisible({ timeout: 10000 });
  });

  test("lists webhooks created via API", async ({ page }) => {
    await createWebhookAPI(token, storeId);

    await page.goto(`/stores/${storeId}/webhooks`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("hooks.example.com")).toBeVisible({
      timeout: 10000,
    });
  });
});
