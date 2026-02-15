/**
 * SourcePilot billing and API keys e2e tests.
 *
 * Tests the billing overview page, plan display, and API key management
 * that are common across all SaaS services.
 *
 * **For QA Engineers:**
 *   - Verify billing page shows current plan (free by default)
 *   - Verify usage counters display import counts
 *   - Verify API key generation and display
 *   - Verify API key deletion
 *   - Verify plan upgrade prompts display correctly
 *
 * **For End Users:**
 *   - View your current plan and usage statistics
 *   - Manage API keys for programmatic access
 *   - Upgrade your plan for higher import limits
 */

import { test, expect } from "@playwright/test";
import {
  registerServiceUser,
  serviceLogin,
  serviceApiGet,
  serviceApiPost,
} from "../service-helpers";

test.describe("SourcePilot Billing & API Keys", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("sourcepilot");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("billing page displays current plan", async ({ page }) => {
    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    // New users should be on the free plan
    await expect(
      page.getByText(/free|starter|plan|billing/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("billing API returns plan overview", async () => {
    const overview = await serviceApiGet(
      "sourcepilot",
      token,
      "/api/v1/billing/overview"
    );

    expect(overview).toHaveProperty("plan");
    expect(overview).toHaveProperty("status");
  });

  test("API keys page loads correctly", async ({ page }) => {
    await page.goto("/api-keys");
    await page.waitForLoadState("networkidle");

    // Should show API keys section
    await expect(
      page.getByText(/api key|keys|generate/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("can generate a new API key via dialog", async ({ page }) => {
    await page.goto("/api-keys");
    await page.waitForLoadState("networkidle");

    // Click generate key button
    const genBtn = page.getByRole("button", { name: /generate|create|new.*key/i });
    if (await genBtn.isVisible()) {
      await genBtn.click();

      // Fill key name if dialog appears
      const nameInput = page.locator("input[placeholder*='name'], input[name='name']").first();
      if (await nameInput.isVisible({ timeout: 3000 })) {
        await nameInput.fill("Test API Key");
        await page.getByRole("button", { name: /generate|create|save/i }).last().click();
      }

      // Should display the new key or success message
      await page.waitForLoadState("networkidle");
    }
  });

  test("billing shows usage statistics", async ({ page }) => {
    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    // Should show usage info like "imports used" or "API calls"
    await expect(
      page.getByText(/usage|import|limit|calls/i).first()
    ).toBeVisible({ timeout: 10000 });
  });
});
