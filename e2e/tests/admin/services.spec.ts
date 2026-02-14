/**
 * Admin services page e2e tests.
 */

import { test, expect } from "@playwright/test";
import { adminLogin, ADMIN_EMAIL, ADMIN_PASSWORD } from "../service-helpers";

test.describe("Admin Services", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  });

  test("displays service health status", async ({ page }) => {
    await page.goto("/services");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: /services/i })).toBeVisible({ timeout: 10000 });
  });
});
