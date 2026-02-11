/**
 * E2E tests for Phase 2 Polish features (Phases 4-5).
 *
 * Tests dashboard enhancements including: platform home KPIs,
 * store overview KPIs, order notes, CSV export buttons,
 * command palette, and inventory alerts.
 *
 * **For Developers:**
 *   These tests cover UI features added in Phase 2 Polish:
 *   - Phase 4: Dashboard enhancements (KPIs, command palette, notifications)
 *   - Phase 5: Data & QoL (CSV export, order notes, inventory alerts)
 *
 * **For QA Engineers:**
 *   - Platform home shows aggregate metrics when stores exist.
 *   - Store overview shows KPI cards (revenue, orders, products).
 *   - Order detail page has an "Internal Notes" textarea.
 *   - Orders and products pages have "Export CSV" buttons.
 *   - Cmd+K opens the command palette modal.
 *   - Low-stock products trigger inventory alert cards on store overview.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createStoreAPI,
  createProductAPI,
  createOrderAPI,
} from "../helpers";

const API_BASE = "http://localhost:8000";

test.describe("Platform Home Dashboard", () => {
  let email: string;
  let password: string;
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, email, password);
  });

  test("shows platform overview with store cards", async ({ page }) => {
    await page.goto("/");
    // Should show the platform home with at least one store card
    await expect(page.getByText(/your stores/i).first()).toBeVisible({ timeout: 10000 });
    // Should have a link/card for the created store
    await expect(page.getByText(/test store/i).first()).toBeVisible({ timeout: 10000 });
  });

  test("shows aggregate metrics section", async ({ page }) => {
    // Create some data for metrics
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    await createOrderAPI(
      (await fetch(`${API_BASE}/api/v1/stores/${storeId}`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then((r) => r.json())).slug,
      "metrics@example.com",
      [{ product_id: product.id, variant_id: variantId, quantity: 1 }]
    );

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Should show aggregate KPI-like content
    // The platform home shows total revenue, orders, products, active stores
    await expect(page.getByText(/revenue/i).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/orders/i).first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Store Overview KPI Dashboard", () => {
  let email: string;
  let password: string;
  let token: string;
  let storeId: string;
  let storeSlug: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    storeSlug = store.slug;
    await dashboardLogin(page, email, password);
  });

  test("shows KPI cards on store overview", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    await page.waitForLoadState("networkidle");

    // Should show KPI metric cards
    await expect(page.getByText(/revenue/i).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/orders/i).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/products/i).first()).toBeVisible({ timeout: 10000 });
  });

  test("shows recent orders section", async ({ page }) => {
    // Create an order
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    await createOrderAPI(storeSlug, "recent@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 1 },
    ]);

    await page.goto(`/stores/${storeId}`);
    await page.waitForLoadState("networkidle");

    // Should show recent orders section
    await expect(page.getByText(/recent orders/i).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("recent@example.com")).toBeVisible({ timeout: 10000 });
  });

  test("shows quick action links", async ({ page }) => {
    await page.goto(`/stores/${storeId}`);
    await page.waitForLoadState("networkidle");

    // Should have quick action links
    await expect(page.getByText(/add product/i).first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Order Notes", () => {
  let email: string;
  let password: string;
  let token: string;
  let storeId: string;
  let storeSlug: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    storeSlug = store.slug;
    await dashboardLogin(page, email, password);
  });

  test("shows internal notes section on order detail", async ({ page }) => {
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const checkout = await createOrderAPI(storeSlug, "notes@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 1 },
    ]);

    await page.goto(`/stores/${storeId}/orders/${checkout.order_id}`);
    await expect(page.getByText(/internal notes/i)).toBeVisible({ timeout: 10000 });
  });

  test("saves order notes on blur", async ({ page }) => {
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const checkout = await createOrderAPI(storeSlug, "savenotes@example.com", [
      { product_id: product.id, variant_id: variantId, quantity: 1 },
    ]);

    await page.goto(`/stores/${storeId}/orders/${checkout.order_id}`);
    await expect(page.getByText(/internal notes/i)).toBeVisible({ timeout: 10000 });

    // Type a note into the textarea
    const textarea = page.locator("textarea").first();
    await textarea.fill("Customer requested express shipping");
    // Blur to trigger auto-save
    await textarea.blur();

    // Wait for save indication
    await expect(page.getByText(/saved/i).first()).toBeVisible({ timeout: 5000 });

    // Reload and verify the note persisted
    await page.reload();
    await expect(page.getByText(/internal notes/i)).toBeVisible({ timeout: 10000 });
    await expect(page.locator("textarea").first()).toHaveValue("Customer requested express shipping");
  });
});

test.describe("CSV Export", () => {
  let email: string;
  let password: string;
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, email, password);
  });

  test("orders page shows export CSV button", async ({ page }) => {
    await page.goto(`/stores/${storeId}/orders`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("button", { name: /export csv/i }).first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("products page shows export CSV button", async ({ page }) => {
    await page.goto(`/stores/${storeId}/products`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("button", { name: /export csv/i }).first()).toBeVisible({
      timeout: 10000,
    });
  });
});

test.describe("Command Palette", () => {
  let email: string;
  let password: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    await createStoreAPI(user.token);
    await dashboardLogin(page, email, password);
  });

  test("opens with Ctrl+K keyboard shortcut", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Press Ctrl+K to open command palette
    await page.keyboard.press("Control+k");

    // Should show the command palette modal with search input
    await expect(page.getByPlaceholder(/search/i).first()).toBeVisible({ timeout: 5000 });
  });

  test("shows page navigation options", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Open command palette
    await page.keyboard.press("Control+k");
    await expect(page.getByPlaceholder(/search/i).first()).toBeVisible({ timeout: 5000 });

    // Should show navigation options
    await expect(page.getByText(/stores/i).first()).toBeVisible({ timeout: 5000 });
  });

  test("closes on Escape", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Open command palette
    await page.keyboard.press("Control+k");
    const searchInput = page.getByPlaceholder(/search/i).first();
    await expect(searchInput).toBeVisible({ timeout: 5000 });

    // Type into input to confirm focus, then close with Escape
    await searchInput.click();
    await searchInput.fill("test");
    await expect(searchInput).toHaveValue("test");

    // Close with Escape (handler is on input's onKeyDown)
    await page.keyboard.press("Escape");

    // Search input should no longer be visible
    await expect(searchInput).not.toBeVisible({ timeout: 10000 });
  });
});

test.describe("Inventory Alerts", () => {
  let email: string;
  let password: string;
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, email, password);
  });

  test("shows low stock alerts for products with low inventory", async ({ page }) => {
    // Create a product with very low stock
    await createProductAPI(token, storeId, {
      title: "Almost Out Widget",
      variants: [{ name: "Default", sku: "LOW-001", price: null, inventory_count: 2 }],
    });

    await page.goto(`/stores/${storeId}`);
    await page.waitForLoadState("networkidle");

    // Should show low stock alert
    await expect(page.getByText(/low stock/i).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Almost Out Widget")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/2 left/i)).toBeVisible({ timeout: 10000 });
  });

  test("does not show alerts when all products have sufficient stock", async ({ page }) => {
    // Create a product with plenty of stock
    await createProductAPI(token, storeId, {
      title: "Well Stocked Item",
      variants: [{ name: "Default", sku: "OK-001", price: null, inventory_count: 100 }],
    });

    await page.goto(`/stores/${storeId}`);
    await page.waitForLoadState("networkidle");

    // Should NOT show low stock alerts
    // Wait a moment for the component to load
    await page.waitForTimeout(2000);
    await expect(page.getByText(/low stock alert/i)).not.toBeVisible();
  });
});
