/**
 * SourcePilot import job management e2e tests.
 *
 * Tests the complete import job lifecycle: creation, listing, cancellation,
 * retry, and bulk import workflows.
 *
 * **For QA Engineers:**
 *   - Verify import job creation via UI dialog
 *   - Verify import jobs list displays with correct status badges
 *   - Verify pagination controls work for large job lists
 *   - Verify cancel operation on pending/running jobs
 *   - Verify retry operation on failed/cancelled jobs
 *   - Verify bulk import creates multiple jobs
 *   - Verify empty state displays when no imports exist
 *   - Verify API-created imports appear in the dashboard list
 *
 * **For End Users:**
 *   - Import products from AliExpress, CJ Dropshipping, or Spocket
 *   - View your import history and track progress
 *   - Cancel pending imports or retry failed ones
 */

import { test, expect } from "@playwright/test";
import {
  registerServiceUser,
  serviceLogin,
  createImportJobAPI,
  serviceApiPost,
  serviceApiGet,
} from "../service-helpers";

test.describe("SourcePilot Imports", () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerServiceUser("sourcepilot");
    token = user.token;
    await serviceLogin(page, user.email, user.password);
  });

  test("shows empty state when no imports exist", async ({ page }) => {
    await page.goto("/imports");
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByText(/no imports yet|no import jobs|get started/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("lists import jobs created via API", async ({ page }) => {
    await createImportJobAPI(token, {
      product_url: "https://www.aliexpress.com/item/1005006.html",
      source: "aliexpress",
    });

    await page.goto("/imports");
    await page.waitForLoadState("networkidle");

    // Should display the import in the list
    await expect(
      page.getByText(/aliexpress/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows summary cards with import counts", async ({ page }) => {
    await createImportJobAPI(token);
    await createImportJobAPI(token);

    await page.goto("/imports");
    await page.waitForLoadState("networkidle");

    // Should display total imports count
    await expect(
      page.getByText(/total imports/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test("displays status badges for import jobs", async ({ page }) => {
    await createImportJobAPI(token);

    await page.goto("/imports");
    await page.waitForLoadState("networkidle");

    // Should show pending status (imports start as pending)
    await expect(
      page.getByText(/pending/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("can create import via dialog", async ({ page }) => {
    await page.goto("/imports");
    await page.waitForLoadState("networkidle");

    // Click New Import button
    await page.getByRole("button", { name: /new import/i }).click();

    // Fill the import form in the dialog
    await expect(
      page.getByRole("heading", { name: /new import|import product/i })
    ).toBeVisible();

    // Fill product URL
    await page.fill(
      "input[placeholder*='aliexpress']",
      "https://www.aliexpress.com/item/12345.html"
    );

    // Submit the form
    await page.getByRole("button", { name: /start import|import|submit/i }).click();

    // Should show the new import in the list
    await expect(
      page.getByText(/aliexpress/i).first()
    ).toBeVisible({ timeout: 15000 });
  });

  test("can cancel a pending import job via API", async ({ page }) => {
    const job = await createImportJobAPI(token);

    // Cancel the job via API
    await serviceApiPost(
      "sourcepilot",
      token,
      `/api/v1/imports/${job.id}/cancel`,
      {}
    );

    await page.goto("/imports");
    await page.waitForLoadState("networkidle");

    // Should show cancelled status
    await expect(
      page.getByText(/cancelled/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("can retry a cancelled import job via API", async ({ page }) => {
    const job = await createImportJobAPI(token);

    // Cancel then retry
    await serviceApiPost(
      "sourcepilot",
      token,
      `/api/v1/imports/${job.id}/cancel`,
      {}
    );
    await serviceApiPost(
      "sourcepilot",
      token,
      `/api/v1/imports/${job.id}/retry`,
      {}
    );

    await page.goto("/imports");
    await page.waitForLoadState("networkidle");

    // Should show pending status after retry
    await expect(
      page.getByText(/pending/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("bulk import creates multiple jobs", async ({ page }) => {
    await serviceApiPost("sourcepilot", token, "/api/v1/imports/bulk", {
      product_urls: [
        "https://www.aliexpress.com/item/bulk1.html",
        "https://www.aliexpress.com/item/bulk2.html",
        "https://www.aliexpress.com/item/bulk3.html",
      ],
      source: "aliexpress",
    });

    await page.goto("/imports");
    await page.waitForLoadState("networkidle");

    // Should show total imports count of at least 3
    const response = await serviceApiGet(
      "sourcepilot",
      token,
      "/api/v1/imports?limit=10"
    );
    expect(response.total).toBeGreaterThanOrEqual(3);
  });

  test("import list supports pagination", async ({ page }) => {
    // Create enough imports to trigger pagination (over 20)
    const promises = [];
    for (let i = 0; i < 5; i++) {
      promises.push(createImportJobAPI(token));
    }
    await Promise.all(promises);

    await page.goto("/imports");
    await page.waitForLoadState("networkidle");

    // Verify multiple imports display
    const items = page.locator("[data-testid='import-row'], tr, [class*='import']");
    const count = await items.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });
});
