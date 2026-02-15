/**
 * RankPilot SEO audit e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createSiteAPI, runSeoAuditAPI } from "../service-helpers";

test.describe("RankPilot Audits", () => {
  let token: string;
  let siteId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("rankpilot");
    token = user.token;
    const site = await createSiteAPI(token, "audit-test.com");
    siteId = site.id;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state when no audits exist", async ({ page }) => {
    await page.goto("/audits");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: /no audits yet/i })).toBeVisible({ timeout: 10000 });
  });

  test("displays audit results from API", async ({ page }) => {
    await runSeoAuditAPI(token, siteId);

    await page.goto("/audits");
    await page.waitForLoadState("networkidle");

    // Site auto-selects the first one; verify audit history heading appears
    await expect(page.getByRole("heading", { name: /audit history/i })).toBeVisible({ timeout: 10000 });
  });
});
