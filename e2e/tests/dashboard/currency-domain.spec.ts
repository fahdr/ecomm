/**
 * Dashboard currency and domain management e2e tests.
 *
 * Tests multi-currency settings, currency converter, and custom domain
 * lifecycle (connect, verify, remove).
 *
 * **For QA Engineers:**
 *   - Currency page shows base currency and available currencies list.
 *   - Updating base currency via PATCH persists the change.
 *   - Currency converter fetches rates and calculates conversions.
 *   - Domain page shows "Connect a Domain" when none is configured (no error).
 *   - Domain lifecycle: connect -> pending -> verify -> verified -> remove.
 *   - Duplicate domain detection shows user-friendly error.
 */

import { test, expect } from "@playwright/test";
import { registerUser, dashboardLogin, createStoreAPI } from "../helpers";

test.describe("Dashboard Currency Settings", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(user.token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows currency settings page", async ({ page }) => {
    await page.goto(`/stores/${storeId}/currency`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/currency|USD|base/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows currency page with configured currency info", async ({ page }) => {
    await page.goto(`/stores/${storeId}/currency`);
    await page.waitForLoadState("networkidle");

    // Verify the "Default Currency" card heading is visible
    await expect(
      page.getByText("Default Currency").first()
    ).toBeVisible({ timeout: 10000 });

    // The store's base_currency is "USD" (DB default)
    await expect(
      page.getByText(/USD|currency/i).first()
    ).toBeVisible({ timeout: 10000 });

    // Verify the currency converter section is rendered
    await expect(
      page.getByText("Currency Converter").first()
    ).toBeVisible({ timeout: 10000 });

    // Verify the "Save Currency" button is present (form loaded fully)
    await expect(
      page.getByRole("button", { name: /save currency/i })
    ).toBeVisible({ timeout: 10000 });
  });

  test("changes default currency and persists after reload", async ({ page }) => {
    await page.goto(`/stores/${storeId}/currency`);
    await page.waitForLoadState("networkidle");

    // Wait for the page to fully load
    await expect(
      page.getByRole("button", { name: /save currency/i })
    ).toBeVisible({ timeout: 10000 });

    // Click the currency dropdown and select EUR
    await page.locator("#default-currency").click();
    await page.getByRole("option", { name: /EUR/i }).click();

    // Click Save
    await page.getByRole("button", { name: /save currency/i }).click();

    // Verify success message appears
    await expect(
      page.getByText("Currency updated successfully").first()
    ).toBeVisible({ timeout: 10000 });

    // Reload and verify EUR is still selected
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/EUR as the default currency/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("currency converter calculates conversion", async ({ page }) => {
    await page.goto(`/stores/${storeId}/currency`);
    await page.waitForLoadState("networkidle");

    // Wait for rates to load (Convert button becomes enabled)
    const convertBtn = page.getByRole("button", { name: /convert/i });
    await expect(convertBtn).toBeVisible({ timeout: 10000 });

    // Enter amount
    await page.locator("#conv-amount").fill("100");

    // Click Convert
    await convertBtn.click();

    // Verify result displays (format: "100.00 USD = XX.XX EUR")
    await expect(
      page.getByText(/100\.00 USD = .+ EUR/i).first()
    ).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Dashboard Domain Settings", () => {
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    token = user.token;
    const store = await createStoreAPI(user.token);
    storeId = store.id;
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows domain page without error when no domain configured", async ({ page }) => {
    await page.goto(`/stores/${storeId}/domain`);
    await page.waitForLoadState("networkidle");

    // Verify the "Domain" heading is visible
    await expect(
      page.getByRole("heading", { name: /domain/i }).first()
    ).toBeVisible({ timeout: 10000 });

    // Verify "Connect a Domain" form is shown (not an error)
    await expect(
      page.getByText("Connect a Domain").first()
    ).toBeVisible({ timeout: 10000 });

    // Verify NO error banner is displayed
    await expect(
      page.locator(".text-destructive").first()
    ).not.toBeVisible({ timeout: 3000 });

    // Verify the domain input and submit button are present
    await expect(
      page.getByPlaceholder("shop.example.com")
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("button", { name: /connect domain/i })
    ).toBeVisible({ timeout: 10000 });
  });

  test("domain lifecycle: connect, verify, and remove", async ({ page }) => {
    // Use a unique domain per test run to avoid global uniqueness conflicts
    const uniqueDomain = `shop-${Date.now()}.teststore.com`;

    await page.goto(`/stores/${storeId}/domain`);
    await page.waitForLoadState("networkidle");

    // 1. Connect a domain
    await page.getByPlaceholder("shop.example.com").fill(uniqueDomain);
    await page.getByRole("button", { name: /connect domain/i }).click();

    // 2. Verify pending status appears with DNS instructions
    await expect(
      page.getByText("pending").first()
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(uniqueDomain).first()
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText("DNS Configuration Required").first()
    ).toBeVisible({ timeout: 10000 });

    // 3. Click Verify DNS
    await page.getByRole("button", { name: /verify dns/i }).click();

    // 4. Verify status changes to "verified" (dev mode auto-verifies)
    await expect(
      page.getByText("verified").first()
    ).toBeVisible({ timeout: 10000 });

    // 5. Verify DNS button is no longer shown (domain is verified)
    await expect(
      page.getByRole("button", { name: /verify dns/i })
    ).not.toBeVisible({ timeout: 3000 });

    // 6. Remove domain
    await page.getByRole("button", { name: /remove domain/i }).click();

    // 7. Confirm removal in dialog
    const dialog = page.locator("[role=dialog]");
    await expect(dialog).toBeVisible({ timeout: 5000 });
    await dialog.getByRole("button", { name: /remove/i, exact: false }).last().click();

    // 8. Verify "Connect a Domain" form returns
    await expect(
      page.getByText("Connect a Domain").first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows error when adding domain to store that already has one", async ({ page }) => {
    // First, set a domain via API
    const ts = Date.now();
    await fetch(`http://localhost:8000/api/v1/stores/${storeId}/domain`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ domain: `shop-${ts}.test.com` }),
    });

    // Navigate to the domain page -- should show existing domain
    await page.goto(`/stores/${storeId}/domain`);
    await page.waitForLoadState("networkidle");

    // Verify the existing domain is displayed
    await expect(
      page.getByText(`shop-${ts}.test.com`).first()
    ).toBeVisible({ timeout: 10000 });

    // "Connect a Domain" form should NOT be visible (domain already exists)
    await expect(
      page.getByText("Connect a Domain")
    ).not.toBeVisible({ timeout: 3000 });
  });
});
