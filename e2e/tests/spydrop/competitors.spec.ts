/**
 * SpyDrop competitor management e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, createCompetitorAPI } from "../service-helpers";

test.describe("SpyDrop Competitors", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("spydrop");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state", async ({ page }) => {
    await page.goto("/competitors");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: /no competitors yet/i })).toBeVisible({ timeout: 10000 });
  });

  test("displays competitors from API", async ({ page }) => {
    await createCompetitorAPI(token, { name: "Competitor Store" });
    await page.goto("/competitors");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("link", { name: /competitor store/i })).toBeVisible({ timeout: 10000 });
  });
});
