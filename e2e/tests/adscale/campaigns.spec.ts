/**
 * AdScale campaign management e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createAdAccountAPI, createAdCampaignAPI } from "../service-helpers";

test.describe("AdScale Campaigns", () => {
  let token: string;
  let accountId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("adscale");
    token = user.token;
    const account = await createAdAccountAPI(token);
    accountId = account.id;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state when no campaigns exist", async ({ page }) => {
    // Create fresh user without campaigns (account exists but no campaigns)
    await page.goto("/campaigns");
    await page.waitForLoadState("networkidle");
    // The page should at least have the campaigns heading
    await expect(page.getByRole("heading", { name: /no campaigns yet/i })).toBeVisible({ timeout: 10000 });
  });

  test("displays campaigns from API", async ({ page }) => {
    await createAdCampaignAPI(token, accountId, { name: "Summer Campaign" });
    await page.goto("/campaigns");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/summer campaign/i)).toBeVisible({ timeout: 10000 });
  });
});
