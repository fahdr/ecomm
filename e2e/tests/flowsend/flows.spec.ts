import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createFlowAPI } from "../service-helpers";

test.describe("FlowSend Flows", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("flowsend");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state", async ({ page }) => {
    await page.goto("/flows");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/no automation flows yet/i)).toBeVisible({ timeout: 10000 });
  });

  test("displays flows from API", async ({ page }) => {
    await createFlowAPI(token, { name: "Welcome Series" });
    await page.goto("/flows");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/welcome series/i)).toBeVisible({ timeout: 10000 });
  });
});
