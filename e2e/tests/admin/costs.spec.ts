/**
 * Admin costs page e2e tests.
 */

import { test, expect } from "@playwright/test";
import { adminLogin, ADMIN_EMAIL, ADMIN_PASSWORD } from "../service-helpers";

test.describe("Admin Costs", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  });

  test("displays LLM usage costs", async ({ page }) => {
    await page.goto("/costs");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: /cost analytics/i })).toBeVisible({ timeout: 10000 });
  });
});
