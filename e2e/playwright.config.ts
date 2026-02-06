/**
 * Playwright configuration for end-to-end tests.
 *
 * Defines two projects — one targeting the dashboard (port 3000)
 * and one targeting the storefront (port 3001). Both share a
 * common Chromium browser instance.
 *
 * **For Developers:**
 *   Run `npm test` from the e2e/ directory. Services must be
 *   running (backend on 8000, dashboard on 3000, storefront on 3001).
 *
 * **For QA Engineers:**
 *   Tests cover full user flows: registration, store creation,
 *   product management, cart, checkout, and order management.
 *   Reports are generated in e2e/playwright-report/.
 */

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: "html",
  timeout: 30000,

  use: {
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    {
      name: "dashboard",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        baseURL: "http://localhost:3000",
      },
      testMatch: /dashboard\/.+\.spec\.ts/,
    },
    {
      name: "storefront",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        baseURL: "http://localhost:3001",
      },
      testMatch: /storefront\/.+\.spec\.ts/,
    },
  ],
});
