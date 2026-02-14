import { test, expect } from "@playwright/test";
import { registerServiceUser, uniqueEmail, TEST_PASSWORD } from "../service-helpers";

test.describe("PostPilot Authentication", () => {
  test("user can register", async ({ page }) => {
    const email = uniqueEmail();
    await page.goto("/register");
    await page.fill("#register-email", email);
    await page.fill("#register-password", TEST_PASSWORD);
    await page.fill("#register-confirm", TEST_PASSWORD);
    await page.getByRole("button", { name: /create account/i }).click();
    // Wait for dashboard content to load
    await expect(page.getByText(/welcome to postpilot/i)).toBeVisible({ timeout: 15000 });
  });
});
