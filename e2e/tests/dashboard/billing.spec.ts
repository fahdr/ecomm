/**
 * Dashboard billing and pricing e2e tests.
 *
 * Tests the pricing page (plan listing, subscribe flow) and billing page
 * (current plan display, usage stats, plan upgrade).
 *
 * **For QA Engineers:**
 *   - Pricing page loads without authentication but shows plan cards.
 *   - Billing page requires authentication and displays current plan/usage.
 *   - Subscribe flow (mock mode) upgrades the user's plan immediately.
 *   - After upgrading, billing page reflects the new plan and usage limits.
 */

import { test, expect } from "@playwright/test";
import {
  registerUser,
  dashboardLogin,
  subscribeUserAPI,
  createStoreAPI,
} from "../helpers";

test.describe("Pricing Page", () => {
  let email: string;
  let password: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    await dashboardLogin(page, email, password);
  });

  test("displays all four plan cards", async ({ page }) => {
    await page.goto("/pricing");
    await page.waitForLoadState("networkidle");

    // Verify all plan names are visible (exact match to avoid "Products" etc.)
    await expect(page.getByText("Free", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Starter", { exact: true })).toBeVisible();
    await expect(page.getByText("Growth", { exact: true })).toBeVisible();
    await expect(page.getByText("Pro", { exact: true })).toBeVisible();
  });

  test("shows current plan badge on free tier", async ({ page }) => {
    await page.goto("/pricing");
    await page.waitForLoadState("networkidle");

    // Free plan should show "Current Plan" badge (use first() since it appears in badge + button)
    await expect(page.getByText("Current Plan").first()).toBeVisible();
  });

  test("displays plan limits and pricing", async ({ page }) => {
    await page.goto("/pricing");
    await page.waitForLoadState("networkidle");

    // Verify pricing is shown
    await expect(page.getByText("$0")).toBeVisible();
    await expect(page.getByText("$29/mo")).toBeVisible();
    await expect(page.getByText("$79/mo")).toBeVisible();
    await expect(page.getByText("$199/mo")).toBeVisible();

    // Verify trial info on paid plans
    await expect(page.getByText("14-day free trial").first()).toBeVisible();
  });

  test("subscribe button redirects on paid plan", async ({ page }) => {
    await page.goto("/pricing");
    await page.waitForLoadState("networkidle");

    // Click Subscribe on the Starter plan card
    const subscribeButtons = page.getByRole("button", { name: "Subscribe" });
    await subscribeButtons.first().click();

    // In mock mode, checkout_url points to the billing success URL
    // which is http://localhost:3000/billing?success=true
    await page.waitForURL(/\/billing\?success=true/, { timeout: 10000 });
    await expect(
      page.getByText("Your subscription has been activated")
    ).toBeVisible();
  });
});

test.describe("Billing Page", () => {
  test("shows free plan for new user", async ({ page }) => {
    const user = await registerUser();
    await dashboardLogin(page, user.email, user.password);

    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    // Should show "Billing" heading
    await expect(
      page.getByRole("heading", { name: "Billing" })
    ).toBeVisible();

    // Current plan card should show "Free" plan
    await expect(page.getByText("Current Plan")).toBeVisible();
    await expect(page.getByText(/free/i).first()).toBeVisible();

    // Should show "Upgrade Plan" button (not "Manage Subscription")
    await expect(
      page.getByRole("link", { name: /upgrade plan/i })
    ).toBeVisible();
  });

  test("shows usage stats for free user", async ({ page }) => {
    const user = await registerUser();
    await dashboardLogin(page, user.email, user.password);

    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    // Usage section should be visible (scope to main to avoid nav link collisions)
    const main = page.getByRole("main");
    await expect(main.getByText("Usage", { exact: true })).toBeVisible();
    await expect(main.getByText("Stores", { exact: true })).toBeVisible();
    await expect(main.getByText("Products per store")).toBeVisible();
    await expect(main.getByText("Orders this month")).toBeVisible();

    // Free plan limits: 1 store, 25 products, 50 orders
    await expect(page.getByText("0 / 1")).toBeVisible();
    await expect(page.getByText("0 / 25")).toBeVisible();
    await expect(page.getByText("0 / 50")).toBeVisible();
  });

  test("shows upgraded plan after subscribing", async ({ page }) => {
    const user = await registerUser();
    await subscribeUserAPI(user.token, "starter");
    await dashboardLogin(page, user.email, user.password);

    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    // Should show Starter plan
    await expect(page.getByText(/starter/i).first()).toBeVisible();

    // Should show active status badge
    await expect(page.getByText("active")).toBeVisible();

    // Should show "Manage Subscription" button instead of "Upgrade"
    await expect(
      page.getByRole("button", { name: /manage subscription/i })
    ).toBeVisible();

    // Starter limits: 3 stores, 100 products, 500 orders
    await expect(page.getByText("0 / 3")).toBeVisible();
    await expect(page.getByText("0 / 100")).toBeVisible();
    await expect(page.getByText("0 / 500")).toBeVisible();
  });

  test("usage updates after creating a store", async ({ page }) => {
    const user = await registerUser();
    await createStoreAPI(user.token, "Billing Test Store");
    await dashboardLogin(page, user.email, user.password);

    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    // Should show 1 store used out of 1 limit
    await expect(page.getByText("1 / 1")).toBeVisible();
  });

  test("navigate from billing to pricing via Change Plan", async ({
    page,
  }) => {
    const user = await registerUser();
    await subscribeUserAPI(user.token, "starter");
    await dashboardLogin(page, user.email, user.password);

    await page.goto("/billing");
    await page.waitForLoadState("networkidle");

    // Click "Change Plan" button
    await page.getByRole("link", { name: /change plan/i }).click();
    await expect(page).toHaveURL(/\/pricing/, { timeout: 5000 });
  });

  test("shows success banner after checkout", async ({ page }) => {
    const user = await registerUser();
    await dashboardLogin(page, user.email, user.password);

    // Navigate directly to billing with success param
    await page.goto("/billing?success=true");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByText("Your subscription has been activated")
    ).toBeVisible();
  });
});

test.describe("Navigation", () => {
  test("billing and pricing links appear in header", async ({ page }) => {
    const user = await registerUser();
    await dashboardLogin(page, user.email, user.password);

    // Check billing link is accessible from home page
    await expect(
      page.getByRole("link", { name: /billing/i }).first()
    ).toBeVisible();

    // Navigate to billing page, then check pricing link is available
    await page.getByRole("link", { name: /billing/i }).first().click();
    await expect(page).toHaveURL(/\/billing/, { timeout: 5000 });
    await expect(
      page.getByRole("link", { name: /pricing|change plan/i }).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("navigate between billing and pricing", async ({ page }) => {
    const user = await registerUser();
    await dashboardLogin(page, user.email, user.password);

    // Go to billing
    await page.getByRole("link", { name: /billing/i }).first().click();
    await expect(page).toHaveURL(/\/billing/, { timeout: 5000 });

    // Navigate to pricing from billing
    await page.getByRole("link", { name: /pricing/i }).first().click();
    await expect(page).toHaveURL(/\/pricing/, { timeout: 5000 });
  });
});
