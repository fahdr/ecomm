/**
 * RankPilot keyword tracking e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createSiteAPI, createTrackedKeywordAPI } from "../service-helpers";

test.describe("RankPilot Keywords", () => {
  let token: string;
  let siteId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("rankpilot");
    token = user.token;
    const site = await createSiteAPI(token, "test-site.com");
    siteId = site.id;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows message when no site selected", async ({ page }) => {
    // Create user with no sites
    const user2 = await registerServiceUser("rankpilot");
    await serviceLogin(page, user2.email, user2.password);

    await page.goto("/keywords");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: /no sites registered/i })).toBeVisible({ timeout: 10000 });
  });

  test("can add keywords for a site", async ({ page }) => {
    await page.goto("/keywords");
    await page.waitForLoadState("networkidle");

    // Select site
    await page.selectOption("#site-select", siteId);

    // Add keyword
    await page.getByRole("button", { name: /add keyword/i }).click();
    await page.fill("#keyword-input", "best seo tools 2026");
    await page.getByRole("button", { name: /add|create/i }).last().click();

    await expect(page.getByText(/best seo tools 2026/i)).toBeVisible({ timeout: 10000 });
  });

  test("displays keywords added via API", async ({ page }) => {
    await createTrackedKeywordAPI(token, siteId, "dropshipping tips");

    await page.goto("/keywords");
    await page.waitForLoadState("networkidle");

    // Select site
    await page.selectOption("#site-select", siteId);

    await expect(page.getByText(/dropshipping tips/i)).toBeVisible({ timeout: 10000 });
  });
});
