/**
 * ContentForge billing e2e tests.
 *
 * Tests billing page and plan display.
 *
 * **For QA Engineers:**
 *   - Verify billing page loads
 *   - Verify plan cards display
 *   - Verify usage metrics
 *
 * **For End Users:**
 *   - View your subscription and usage
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin } from "../service-helpers";

test.describe("ContentForge Billing", () => {
  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("contentforge");
    await serviceLogin(page, user.email, user.password);
  });

  test("displays billing page with current plan", async ({ page }) => {
    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/billing & usage/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/current plan/i)).toBeVisible();
  });

  test("shows plan comparison cards", async ({ page }) => {
    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/available plans/i)).toBeVisible();
  });
});
