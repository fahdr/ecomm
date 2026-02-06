/**
 * Shared helpers for Playwright e2e tests.
 *
 * Provides utility functions for common operations like user registration,
 * login, store creation, and product creation. Uses the backend API directly
 * for setup steps to keep tests focused on UI interactions.
 *
 * **For Developers:**
 *   Import these helpers in your test files. Each helper generates unique
 *   data using timestamps to avoid collisions between test runs.
 *
 * **For QA Engineers:**
 *   Helpers call the backend API at http://localhost:8000 to seed data.
 *   The dashboard runs on port 3000 and storefront on port 3001.
 */

import { type Page } from "@playwright/test";

const API_BASE = "http://localhost:8000";

/**
 * Wait until a JWT token is accepted by the backend.
 *
 * After registration the DB transaction may not be fully committed
 * by the time the response arrives. This helper polls /auth/me until
 * the token is recognised, avoiding race-condition 401 errors.
 *
 * @param token - JWT access token to verify.
 * @param maxWaitMs - Maximum time to wait (default 3000ms).
 */
async function waitForToken(token: string, maxWaitMs = 3000): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) return;
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error("Token not valid after waiting — DB commit may be stuck");
}

/** Generate a unique email for test isolation. */
export function uniqueEmail(): string {
  return `test-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`;
}

/** Default test password. */
export const TEST_PASSWORD = "testpass123";

/**
 * Register a user via the API and return credentials.
 *
 * @param email - Optional email; generated if not provided.
 * @returns Object with email, password, and JWT token.
 */
export async function registerUser(email?: string) {
  const userEmail = email || uniqueEmail();
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: userEmail, password: TEST_PASSWORD }),
  });
  if (!res.ok) throw new Error(`Register failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  await waitForToken(data.access_token);
  return { email: userEmail, password: TEST_PASSWORD, token: data.access_token };
}

/**
 * Login a user via the API and return the token.
 *
 * @param email - The user's email.
 * @param password - The user's password.
 * @returns The JWT access token.
 */
export async function loginUser(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  return data.access_token;
}

/**
 * Create a store via the API, retrying on transient 401 errors.
 *
 * After registration, the DB transaction may not be fully committed
 * when the first API call is made. This helper retries a few times
 * to handle that race condition.
 *
 * @param token - JWT access token.
 * @param name - Store name.
 * @returns The created store object with id and slug.
 */
export async function createStoreAPI(token: string, name?: string) {
  const storeName = name || `Test Store ${Date.now()}`;
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
        description: "A test store for e2e tests",
      }),
    });
    if (res.ok) return await res.json();
    if (res.status === 401 && attempt < 4) {
      await new Promise((r) => setTimeout(r, 200));
      continue;
    }
    throw new Error(`Create store failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Create a product via the API, retrying on transient errors.
 *
 * Retries on 401/404 to handle race conditions where the store
 * or user may not yet be committed in the database.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param overrides - Optional product field overrides.
 * @returns The created product object.
 */
export async function createProductAPI(
  token: string,
  storeId: string,
  overrides: Record<string, unknown> = {}
) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${API_BASE}/api/v1/stores/${storeId}/products`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        title: `Test Product ${Date.now()}`,
        price: "29.99",
        status: "active",
        variants: [
          { name: "Default", sku: "TST-001", price: null, inventory_count: 100 },
        ],
        ...overrides,
      }),
    });
    if (res.ok) return await res.json();
    if ((res.status === 401 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 200));
      continue;
    }
    throw new Error(`Create product failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Login via the dashboard UI.
 *
 * Navigates to /login, fills credentials, and submits.
 * Waits for redirect to /stores after successful login.
 *
 * @param page - Playwright page instance.
 * @param email - User email.
 * @param password - User password.
 */
export async function dashboardLogin(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.getByRole("button", { name: /sign in/i }).click();
  // Auth redirects to "/" (dashboard home) after login.
  await page.waitForURL(/\/$/, { timeout: 10000 });
  await page.waitForLoadState("networkidle");
}
