/**
 * FlowSend authentication e2e tests.
 */

import { test, expect } from "@playwright/test";
import { registerServiceUser, serviceLogin, uniqueEmail, TEST_PASSWORD } from "../service-helpers";

test.describe("FlowSend Authentication", () => {
  test("user can register and login", async ({ page }) => {
    const email = uniqueEmail();

    await page.goto("/register");
    await page.fill("#register-email", email);
    await page.fill("#register-password", TEST_PASSWORD);
    await page.fill("#register-confirm", TEST_PASSWORD);
    await page.getByRole("button", { name: /create account/i }).click();

    // Wait for dashboard content to load
    await expect(page.getByText(/welcome to flowsend/i)).toBeVisible({ timeout: 15000 });
  });

  test("protected routes redirect to login", async ({ page }) => {
    await page.goto("/campaigns");
    await page.waitForURL(/\/login/, { timeout: 10000 });
  });
});
