/**
 * TrendScout billing e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin } from "../service-helpers";

test.describe("TrendScout Billing", () => {
  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("trendscout");
    await serviceLogin(page, user.email, user.password);
  });

  test("displays billing page with current plan", async ({ page }) => {
    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: /billing & usage/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/current plan/i).first()).toBeVisible();
  });

  test("shows plan comparison cards", async ({ page }) => {
    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: /available plans/i })).toBeVisible({ timeout: 10000 });
  });

  test("displays API usage metrics", async ({ page }) => {
    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/api usage this period/i)).toBeVisible({ timeout: 10000 });
  });

  test("shows manage subscription button", async ({ page }) => {
    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("button", { name: /manage subscription/i })).toBeVisible();
  });
});
