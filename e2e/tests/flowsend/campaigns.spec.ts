import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createCampaignAPI } from "../service-helpers";

test.describe("FlowSend Campaigns", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("flowsend");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state", async ({ page }) => {
    await page.goto("/campaigns");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/no campaigns yet/i)).toBeVisible({ timeout: 10000 });
  });

  test("displays campaigns from API", async ({ page }) => {
    await createCampaignAPI(token, { name: "Spring Sale" });
    await page.goto("/campaigns");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/spring sale/i)).toBeVisible({ timeout: 10000 });
  });
});
