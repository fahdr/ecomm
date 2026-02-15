import { test, expect } from "@playwright/test";
import { adminLogin, ADMIN_EMAIL, ADMIN_PASSWORD } from "../service-helpers";

test.describe("Admin Authentication", () => {
  test("admin can login", async ({ page }) => {
    await adminLogin(page, ADMIN_EMAIL, ADMIN_PASSWORD);
    // Wait for dashboard content to load
    await expect(page.getByText(/platform overview/i)).toBeVisible({ timeout: 15000 });
  });
});
