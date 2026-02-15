/**
 * TrendScout API keys e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin } from "../service-helpers";

test.describe("TrendScout API Keys", () => {
  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("trendscout");
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state when no API keys exist", async ({ page }) => {
    await page.goto("/api-keys");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: /no api keys yet/i })).toBeVisible({ timeout: 10000 });
  });

  test("can create an API key via dialog", async ({ page }) => {
    await page.goto("/api-keys");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: /create key/i }).first().click();

    // Dialog should open
    await expect(page.getByRole("heading", { name: /create api key/i })).toBeVisible();

    // Fill form
    await page.fill("#key-name", "Production Server");

    // Submit — click Create button inside the dialog
    await page.locator("[role=dialog]").getByRole("button", { name: /create/i }).click();

    // Should show success banner with the created key
    await expect(page.getByText(/api key created successfully/i)).toBeVisible({ timeout: 10000 });
  });

  test("shows API keys page heading and create button", async ({ page }) => {
    await page.goto("/api-keys");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: /api keys/i }).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole("button", { name: /create key/i }).first()).toBeVisible();
  });
});
