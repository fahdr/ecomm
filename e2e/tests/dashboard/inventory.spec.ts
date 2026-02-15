/**
 * End-to-end tests for the inventory management feature.
 *
 * Tests warehouse management, inventory level tracking, stock adjustments,
 * and the inventory dashboard pages for ecommerce mode stores.
 *
 * **For Developers:**
 *   Uses API helpers to seed data, then verifies dashboard UI reflects
 *   the state. The backend runs on port 8000, dashboard on port 3000.
 *
 * **For QA Engineers:**
 *   - Tests require both backend and dashboard services to be running.
 *   - Ecommerce stores auto-create a default warehouse on creation.
 *   - Inventory levels are set via API, then verified in the UI.
 *   - Low-stock alerts appear when quantity <= reorder_point.
 *
 * **For Project Managers:**
 *   10 e2e tests covering the full inventory management user flow,
 *   from warehouse creation to stock adjustments and low-stock alerts.
 *
 * **For End Users:**
 *   These tests verify the inventory management workflows you'll use
 *   in the dashboard to track stock across your warehouses.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  createProductAPI,
  apiGet,
} from "../helpers";

const API_BASE = "http://localhost:8000";

/**
 * Create an ecommerce store via the API.
 *
 * @param token - JWT access token.
 * @param name - Store display name.
 * @returns The created store object with id and slug.
 */
async function createEcommerceStoreAPI(token: string, name?: string) {
  const storeName = name || `Ecom Store ${Date.now()}`;
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${API_BASE}/api/v1/stores`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name: storeName,
        niche: "electronics",
        store_type: "ecommerce",
      }),
    });
    if (res.ok) return await res.json();
    if (res.status === 401 && attempt < 4) {
      await new Promise((r) => setTimeout(r, 200));
      continue;
    }
    throw new Error(`Create ecommerce store failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Create a warehouse via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param name - Warehouse name.
 * @param isDefault - Whether this warehouse is the default.
 * @returns The created warehouse object.
 */
async function createWarehouseAPI(
  token: string,
  storeId: string,
  name: string,
  isDefault = false,
) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${API_BASE}/api/v1/stores/${storeId}/warehouses`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name,
        address: "123 Test St",
        city: "Testville",
        state: "TX",
        country: "US",
        zip_code: "75001",
        is_default: isDefault,
      }),
    });
    if (res.ok) return await res.json();
    if ((res.status === 401 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 300));
      continue;
    }
    throw new Error(`Create warehouse failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * List warehouses via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @returns Array of warehouse objects.
 */
async function listWarehousesAPI(token: string, storeId: string) {
  return apiGet(token, `/api/v1/stores/${storeId}/warehouses`);
}

/**
 * Set inventory level via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param variantId - Product variant UUID.
 * @param warehouseId - Warehouse UUID.
 * @param quantity - Stock quantity.
 * @param reorderPoint - Low-stock alert threshold.
 * @param reorderQuantity - Suggested reorder amount.
 * @returns The inventory level response.
 */
async function setInventoryAPI(
  token: string,
  storeId: string,
  variantId: string,
  warehouseId: string,
  quantity: number,
  reorderPoint = 0,
  reorderQuantity = 0,
) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${API_BASE}/api/v1/stores/${storeId}/inventory`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        variant_id: variantId,
        warehouse_id: warehouseId,
        quantity,
        reorder_point: reorderPoint,
        reorder_quantity: reorderQuantity,
      }),
    });
    if (res.ok) return await res.json();
    if ((res.status === 401 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 300));
      continue;
    }
    throw new Error(`Set inventory failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Adjust inventory via the API.
 *
 * @param token - JWT access token.
 * @param storeId - Store UUID.
 * @param levelId - Inventory level UUID.
 * @param change - Quantity delta.
 * @param reason - Adjustment reason.
 * @returns The updated inventory level.
 */
async function adjustInventoryAPI(
  token: string,
  storeId: string,
  levelId: string,
  change: number,
  reason = "received",
) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(
      `${API_BASE}/api/v1/stores/${storeId}/inventory/${levelId}/adjust`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          quantity_change: change,
          reason,
          notes: `E2E adjustment: ${reason}`,
        }),
      },
    );
    if (res.ok) return await res.json();
    if ((res.status === 401 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 300));
      continue;
    }
    throw new Error(`Adjust inventory failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Delete a warehouse via the API.
 *
 * @param token - JWT access token.
 * @param storeId - Store UUID.
 * @param warehouseId - Warehouse UUID.
 * @returns True if deleted (204), false otherwise.
 */
async function deleteWarehouseAPI(
  token: string,
  storeId: string,
  warehouseId: string,
): Promise<boolean> {
  const res = await fetch(
    `${API_BASE}/api/v1/stores/${storeId}/warehouses/${warehouseId}`,
    {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  return res.status === 204;
}

test.describe("Dashboard Inventory Management", () => {
  let email: string;
  let password: string;
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    token = user.token;
    const store = await createEcommerceStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, email, password);
  });

  test("inventory page loads for ecommerce store", async ({ page }) => {
    await page.goto(`/stores/${storeId}/inventory`);
    await page.waitForLoadState("networkidle");
    // The page should render without errors — look for heading or summary cards
    await expect(
      page.getByRole("heading", { name: /inventory/i }).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("can create a warehouse via API and see it listed", async ({ page }) => {
    await createWarehouseAPI(token, storeId, "East Coast WH");
    await page.goto(`/stores/${storeId}/warehouses`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("East Coast WH")).toBeVisible({ timeout: 10000 });
  });

  test("warehouse details page shows info", async ({ page }) => {
    const warehouses = await listWarehousesAPI(token, storeId);
    const defaultWH = warehouses[0];
    await page.goto(`/stores/${storeId}/warehouses`);
    await page.waitForLoadState("networkidle");
    // The default warehouse name should be visible
    await expect(page.getByText(defaultWH.name)).toBeVisible({ timeout: 10000 });
    // Default badge should be visible
    await expect(page.getByText(/default/i).first()).toBeVisible({ timeout: 10000 });
  });

  test("can set inventory level via API and see it on inventory page", async ({
    page,
  }) => {
    // Create product and set inventory
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const warehouses = await listWarehousesAPI(token, storeId);
    const whId = warehouses[0].id;
    await setInventoryAPI(token, storeId, variantId, whId, 150);

    await page.goto(`/stores/${storeId}/inventory`);
    await page.waitForLoadState("networkidle");
    // Should see quantity in the table or summary
    await expect(page.getByText("150").first()).toBeVisible({ timeout: 10000 });
  });

  test("low stock alert shows when below reorder point", async ({ page }) => {
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const warehouses = await listWarehousesAPI(token, storeId);
    const whId = warehouses[0].id;
    // Set quantity below reorder point
    await setInventoryAPI(token, storeId, variantId, whId, 3, 10, 50);

    await page.goto(`/stores/${storeId}/inventory`);
    await page.waitForLoadState("networkidle");
    // Should see low stock indicator
    await expect(
      page.getByText(/low stock/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("inventory summary shows correct totals", async ({ page }) => {
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const warehouses = await listWarehousesAPI(token, storeId);
    const whId = warehouses[0].id;
    await setInventoryAPI(token, storeId, variantId, whId, 200);

    await page.goto(`/stores/${storeId}/inventory`);
    await page.waitForLoadState("networkidle");
    // Should see total in stock somewhere in summary cards
    await expect(page.getByText("200").first()).toBeVisible({ timeout: 10000 });
  });

  test("can adjust inventory via API and see updated quantity", async ({
    page,
  }) => {
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const warehouses = await listWarehousesAPI(token, storeId);
    const whId = warehouses[0].id;
    const level = await setInventoryAPI(token, storeId, variantId, whId, 100);

    // Adjust +25
    await adjustInventoryAPI(token, storeId, level.id, 25, "received");

    await page.goto(`/stores/${storeId}/inventory`);
    await page.waitForLoadState("networkidle");
    // Should see updated quantity 125
    await expect(page.getByText("125").first()).toBeVisible({ timeout: 10000 });
  });

  test("adjustment history lists changes", async ({ page }) => {
    const product = await createProductAPI(token, storeId);
    const variantId = product.variants[0].id;
    const warehouses = await listWarehousesAPI(token, storeId);
    const whId = warehouses[0].id;
    const level = await setInventoryAPI(token, storeId, variantId, whId, 100);
    await adjustInventoryAPI(token, storeId, level.id, -10, "sold");

    await page.goto(`/stores/${storeId}/inventory`);
    await page.waitForLoadState("networkidle");

    // Look for adjustment history or the sold reason text
    // The page should display adjustment records
    await expect(
      page.getByText(/sold/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("can delete non-default warehouse via API", async ({ page }) => {
    // Create an extra warehouse
    const wh = await createWarehouseAPI(token, storeId, "Temp Warehouse");
    const deleted = await deleteWarehouseAPI(token, storeId, wh.id);
    expect(deleted).toBe(true);

    await page.goto(`/stores/${storeId}/warehouses`);
    await page.waitForLoadState("networkidle");
    // Temp warehouse should not appear
    await expect(page.getByText("Temp Warehouse")).not.toBeVisible({
      timeout: 5000,
    });
  });

  test("dropshipping stores don't show inventory section in nav", async ({
    page,
  }) => {
    // Create a dropshipping store
    const dropRes = await fetch(`${API_BASE}/api/v1/stores`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name: `Drop Store ${Date.now()}`,
        niche: "fashion",
        store_type: "dropshipping",
      }),
    });
    const dropStore = await dropRes.json();

    await page.goto(`/stores/${dropStore.id}`);
    await page.waitForLoadState("networkidle");

    // Inventory and Warehouses links should NOT be visible for dropshipping stores
    // Check that the sidebar does not contain inventory links
    const inventoryLink = page.locator(`a[href*="/stores/${dropStore.id}/inventory"]`);
    await expect(inventoryLink).not.toBeVisible({ timeout: 5000 });
  });
});
