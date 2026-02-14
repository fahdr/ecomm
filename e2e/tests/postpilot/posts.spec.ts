import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createSocialAccountAPI, createSocialPostAPI } from "../service-helpers";

test.describe("PostPilot Posts", () => {
  let token: string;
  let accountId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("postpilot");
    token = user.token;
    const account = await createSocialAccountAPI(token);
    accountId = account.id;
    await serviceLogin(page, user.email, user.password);
  });

  test("displays posts from API", async ({ page }) => {
    await createSocialPostAPI(token, accountId, { content: "Test post content" });
    await page.goto("/posts");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/test post content/i)).toBeVisible({ timeout: 10000 });
  });
});
