/**
 * ContentForge content generation e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, generateContentAPI } from "../service-helpers";

test.describe("ContentForge Content Generation", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("contentforge");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state when no content exists", async ({ page }) => {
    await page.goto("/content");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: /no generations yet/i })).toBeVisible({ timeout: 10000 });
  });

  test("can create content generation via dialog", async ({ page }) => {
    await page.goto("/content");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: /new generation/i }).click();

    await expect(page.getByRole("heading", { name: /new content generation/i })).toBeVisible();

    // Fill product details
    await page.fill("#gen-name", "Wireless Bluetooth Headphones");
    await page.fill("#gen-price", "49.99");
    await page.fill("#gen-category", "Electronics");
    await page.fill("#gen-features", "Noise cancelling, 30hr battery");

    // Generate — click the Generate button inside the dialog
    await page.locator("[role=dialog]").getByRole("button", { name: /generate/i }).click();

    // Should show in list
    await expect(page.getByText(/wireless bluetooth headphones/i)).toBeVisible({ timeout: 15000 });
  });

  test("displays content generated via API", async ({ page }) => {
    await generateContentAPI(token, {
      source_data: { name: "Premium Leather Wallet" },
      content_types: ["description"],
    });

    await page.goto("/content");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/premium leather wallet/i)).toBeVisible({ timeout: 10000 });
  });

  test("shows pagination for multiple content items", async ({ page }) => {
    // Create multiple items
    for (let i = 0; i < 3; i++) {
      await generateContentAPI(token, {
        source_data: { name: `Product ${i}` },
        content_types: ["description"],
      });
    }

    await page.goto("/content");
    await page.waitForLoadState("networkidle");

    // Should show at least one generated item
    await expect(page.getByText(/product/i).first()).toBeVisible({ timeout: 10000 });
  });
});
