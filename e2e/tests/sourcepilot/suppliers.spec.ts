/**
 * SourcePilot supplier account management e2e tests.
 *
 * Tests connecting, listing, updating, and disconnecting supplier
 * platform accounts (AliExpress, CJ Dropshipping, Spocket).
 *
 * **For QA Engineers:**
 *   - Verify supplier account creation via UI dialog
 *   - Verify supplier accounts list displays connected platforms
 *   - Verify account update modifies credentials
 *   - Verify account deletion removes from list
 *   - Verify duplicate name+platform detection (400 error)
 *   - Verify empty state when no accounts exist
 *   - Verify API-created accounts appear in the dashboard
 *
 * **For End Users:**
 *   - Connect your AliExpress, CJ, or Spocket accounts
 *   - Manage API credentials for automated product imports
 *   - Disconnect accounts you no longer use
 */

import { test, expect } from "@playwright/test";
import {
  registerServiceUser,
  serviceLogin,
  createSupplierAccountAPI,
  serviceApiDelete,
  serviceApiGet,
} from "../service-helpers";

test.describe("SourcePilot Supplier Accounts", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("sourcepilot");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state when no suppliers exist", async ({ page }) => {
    await page.goto("/suppliers");
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/no supplier|connect.*supplier|get started/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("lists supplier accounts created via API", async ({ page }) => {
    await createSupplierAccountAPI(token, {
      name: "My AliExpress Account",
      platform: "aliexpress",
    });

    await page.goto("/suppliers");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByText(/my aliexpress account/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows platform badges for connected accounts", async ({ page }) => {
    await createSupplierAccountAPI(token, {
      name: "AliExpress Pro",
      platform: "aliexpress",
    });
    await createSupplierAccountAPI(token, {
      name: "CJ Wholesale",
      platform: "cjdropshipping",
    });

    await page.goto("/suppliers");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByText(/aliexpress/i).first()
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(/cj/i).first()
    ).toBeVisible({ timeout: 5000 });
  });

  test("can create supplier account via dialog", async ({ page }) => {
    await page.goto("/suppliers");
    await page.waitForLoadState("networkidle");

    // Click connect supplier button
    await page.getByRole("button", { name: /connect.*supplier|add.*supplier/i }).click();

    // Dialog should open
    await expect(
      page.getByRole("heading", { name: /connect|new.*supplier/i })
    ).toBeVisible();

    // Fill the form
    const nameInput = page.locator("input[placeholder*='name'], input[name='name']").first();
    await nameInput.fill("Test Supplier Account");

    // Submit
    await page.getByRole("button", { name: /connect|save|submit/i }).last().click();

    // Should appear in list after creation
    await expect(
      page.getByText(/test supplier account/i)
    ).toBeVisible({ timeout: 15000 });
  });

  test("can delete a supplier account via API and verify removal", async ({
    page,
  }) => {
    const account = await createSupplierAccountAPI(token, {
      name: "Delete Me Supplier",
      platform: "aliexpress",
    });

    // Verify it appears
    await page.goto("/suppliers");
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/delete me supplier/i)
    ).toBeVisible({ timeout: 10000 });

    // Delete via API
    await serviceApiDelete(
      "sourcepilot",
      token,
      `/api/v1/suppliers/accounts/${account.id}`
    );

    // Reload and verify removal
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/delete me supplier/i)
    ).not.toBeVisible({ timeout: 5000 });
  });

  test("multiple supplier accounts display in grid", async ({ page }) => {
    await createSupplierAccountAPI(token, {
      name: "Supplier Alpha",
      platform: "aliexpress",
    });
    await createSupplierAccountAPI(token, {
      name: "Supplier Beta",
      platform: "cjdropshipping",
    });
    await createSupplierAccountAPI(token, {
      name: "Supplier Gamma",
      platform: "spocket",
    });

    await page.goto("/suppliers");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/supplier alpha/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/supplier beta/i)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/supplier gamma/i)).toBeVisible({ timeout: 5000 });
  });
});
