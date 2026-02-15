/**
 * RankPilot site management e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createSiteAPI } from "../service-helpers";

test.describe("RankPilot Sites", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("rankpilot");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state when no sites exist", async ({ page }) => {
    await page.goto("/sites");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/no sites tracked yet/i)).toBeVisible({ timeout: 10000 });
  });

  test("can add a site via dialog", async ({ page }) => {
    await page.goto("/sites");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: /add site/i }).first().click();

    // Wait for dialog to appear
    await expect(page.getByRole("heading", { name: /add site/i })).toBeVisible();

    await page.fill("#site-domain", "mystore.com");
    // Click the dialog's submit button (inside the dialog footer)
    await page.locator("[role=dialog]").getByRole("button", { name: /add site/i }).click();

    await expect(page.getByText(/mystore\.com/i)).toBeVisible({ timeout: 10000 });
  });

  test("displays sites created via API", async ({ page }) => {
    await createSiteAPI(token, "example-site.com");

    await page.goto("/sites");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/example-site\.com/i)).toBeVisible({ timeout: 10000 });
  });
});
