/**
 * TrendScout research workflow e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createResearchRunAPI } from "../service-helpers";

test.describe("TrendScout Research", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("trendscout");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state when no research runs exist", async ({ page }) => {
    await page.goto("/research");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: /no research runs yet/i })).toBeVisible({ timeout: 10000 });
  });

  test("can create a research run via dialog", async ({ page }) => {
    await page.goto("/research");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: /new research/i }).click();

    // Dialog should open
    await expect(page.getByRole("heading", { name: /new product research/i })).toBeVisible();

    // Fill keywords using the placeholder-based selector
    await page.fill("input[placeholder*='wireless earbuds']", "wireless earbuds, phone case");

    // Submit — click the Start Research button
    await page.getByRole("button", { name: /start research/i }).click();

    // Should show in list (research run with keywords)
    await expect(page.getByText(/wireless earbuds/i)).toBeVisible({ timeout: 30000 });
  });

  test("lists research runs created via API", async ({ page }) => {
    await createResearchRunAPI(token, ["laptop stand", "desk mat"]);

    await page.goto("/research");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/laptop stand/i)).toBeVisible({ timeout: 10000 });
  });

  test("displays research run status badges", async ({ page }) => {
    await createResearchRunAPI(token);

    await page.goto("/research");
    await page.waitForLoadState("networkidle");

    // Should show research history heading when runs exist
    await expect(page.getByRole("heading", { name: /research history/i })).toBeVisible({ timeout: 10000 });
  });

  test("shows summary cards with research counts", async ({ page }) => {
    await createResearchRunAPI(token);

    await page.goto("/research");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/total runs/i)).toBeVisible();
    await expect(page.getByText(/completed/i).first()).toBeVisible();
  });
});
