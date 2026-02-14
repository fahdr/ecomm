/**
 * Playwright configuration for end-to-end tests.
 *
 * Defines projects for all platform services:
 * - Dashboard (port 3000) — dropshipping merchant dashboard
 * - Storefront (port 3001) — public-facing customer storefront
 * - TrendScout (port 3101) — product research dashboard
 * - ContentForge (port 3102) — AI content generation dashboard
 * - RankPilot (port 3103) — SEO rank tracking dashboard
 * - FlowSend (port 3104) — email marketing dashboard
 * - SpyDrop (port 3105) — competitor intelligence dashboard
 * - PostPilot (port 3106) — social media scheduling dashboard
 * - AdScale (port 3107) — ad campaign optimization dashboard
 * - ShopChat (port 3108) — AI chatbot dashboard
 * - Admin (port 3300) — super admin dashboard
 *
 * **For Developers:**
 *   Run `npm test` from the e2e/ directory. All services must be running.
 *   Use `npx playwright test --project=trendscout` to run a single service.
 *
 * **For QA Engineers:**
 *   Tests cover full user flows per service. Reports in e2e/playwright-report/.
 *   Seed data tests validate pre-populated demo data across all services.
 *
 * **For Project Managers:**
 *   Each service has its own project so tests can be run independently.
 *   The single-worker config prevents system overload during full runs.
 *
 * **For End Users:**
 *   These tests verify the same workflows you perform in each dashboard.
 */

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
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
    {
      name: "trendscout",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        baseURL: "http://localhost:3101",
      },
      testMatch: /trendscout\/.+\.spec\.ts/,
    },
    {
      name: "contentforge",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        baseURL: "http://localhost:3102",
      },
      testMatch: /contentforge\/.+\.spec\.ts/,
    },
    {
      name: "rankpilot",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        baseURL: "http://localhost:3103",
      },
      testMatch: /rankpilot\/.+\.spec\.ts/,
    },
    {
      name: "flowsend",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        baseURL: "http://localhost:3104",
      },
      testMatch: /flowsend\/.+\.spec\.ts/,
    },
    {
      name: "spydrop",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        baseURL: "http://localhost:3105",
      },
      testMatch: /spydrop\/.+\.spec\.ts/,
    },
    {
      name: "postpilot",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        baseURL: "http://localhost:3106",
      },
      testMatch: /postpilot\/.+\.spec\.ts/,
    },
    {
      name: "adscale",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        baseURL: "http://localhost:3107",
      },
      testMatch: /adscale\/.+\.spec\.ts/,
    },
    {
      name: "shopchat",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        baseURL: "http://localhost:3108",
      },
      testMatch: /shopchat\/.+\.spec\.ts/,
    },
    {
      name: "admin",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        baseURL: "http://localhost:3300",
      },
      testMatch: /admin\/.+\.spec\.ts/,
    },
  ],
});
