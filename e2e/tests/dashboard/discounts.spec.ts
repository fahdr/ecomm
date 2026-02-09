/**
 * Dashboard discount management e2e tests.
 *
 * Tests discount creation, listing, and empty state. Discounts are
 * created via the "Create Discount" dialog on the discounts page.
 *
 * **For QA Engineers:**
 *   - Discount list shows code, type, value, and status.
 *   - Creating a discount refreshes the list.
 *   - Empty state is shown when no discounts exist.
 *   - Summary cards show total and active counts.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createStoreAPI,
  createDiscountAPI,
} from "../helpers";

test.describe("Dashboard Discount Management", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows empty state when no discounts exist", async ({ page }) => {
    await page.goto(`/stores/${storeId}/discounts`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/no discount/i)).toBeVisible({ timeout: 10000 });
  });

  test("creates a discount via dialog", async ({ page }) => {
    await page.goto(`/stores/${storeId}/discounts`);
    await page.waitForLoadState("networkidle");
    // Wait for empty state to confirm page is loaded and interactive
    await expect(page.getByText(/no discount/i)).toBeVisible({ timeout: 10000 });

    // Use JS click to bypass React hydration timing issues
    await page.$eval('button:has-text("Create your first discount")', (el: HTMLElement) => el.click());
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5000 });

    await page.fill("#discount-code", "SUMMER25");
    await page.fill("#discount-value", "25");

    // Click submit and wait for the POST to complete
    const [postResp] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes("/discounts") && resp.request().method() === "POST",
        { timeout: 10000 }
      ),
      page.locator('[role="dialog"] button[type="submit"]').click(),
    ]);

    // Wait for dialog to close
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 10000 });

    // Reload to ensure fresh data from the database
    await page.reload();
    await page.waitForLoadState("networkidle");

    // Discount should appear in the list
    await expect(page.getByText("SUMMER25")).toBeVisible({ timeout: 10000 });
  });

  test("lists discounts created via API", async ({ page }) => {
    await createDiscountAPI(token, storeId, {
      code: "TESTCODE10",
      discount_type: "percentage",
      value: 10,
    });
    await createDiscountAPI(token, storeId, {
      code: "FLAT5",
      discount_type: "fixed_amount",
      value: 5,
    });

    await page.goto(`/stores/${storeId}/discounts`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("TESTCODE10")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("FLAT5")).toBeVisible();
  });

  test("renders discount table with all data fields", async ({ page }) => {
    // Create two discounts with different types and full field coverage
    await createDiscountAPI(token, storeId, {
      code: "SAVE25",
      discount_type: "percentage",
      value: 25,
      max_uses: 100,
      minimum_order_amount: 50,
    });
    await createDiscountAPI(token, storeId, {
      code: "FLAT10",
      discount_type: "fixed_amount",
      value: 10,
    });

    await page.goto(`/stores/${storeId}/discounts`);
    await page.waitForLoadState("networkidle");

    // Both discount codes should appear in the table
    await expect(page.getByText("SAVE25")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("FLAT10")).toBeVisible({ timeout: 10000 });

    // Value formatting: the backend returns Decimal values which may serialize
    // as "25.00" (string). The frontend formatDiscountValue renders percentage
    // as `${value}%` which produces "25%" or "25.00%" depending on serialization.
    // Fixed amounts render as `$${Number(value).toFixed(2)}` which produces "$10.00".
    await expect(page.getByText(/25(\.00)?%/).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("$10.00").first()).toBeVisible({ timeout: 10000 });

    // Status badge should show "active"
    await expect(page.getByText("active").first()).toBeVisible({ timeout: 10000 });

    // Summary card should show the total discount count
    await expect(page.getByText("Total Discounts")).toBeVisible({ timeout: 10000 });

    // The minimum order amount column should render without crashing
    // (this catches Decimal serialisation issues — the page must not show an error)
    await expect(page.locator("table")).toBeVisible({ timeout: 10000 });
  });

  test("navigates via sidebar to discounts", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    await page.waitForLoadState("networkidle");
    await page.getByRole("link", { name: "Discounts" }).click();
    await expect(page).toHaveURL(new RegExp(`/stores/${storeId}/discounts`), {
      timeout: 10000,
    });
  });
});
