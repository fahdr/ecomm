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
 * Subscribe a user to a paid plan via the API (mock mode).
 *
 * In mock mode (no Stripe keys), the checkout endpoint creates the
 * subscription record directly in the database and upgrades the
 * user's plan immediately.
 *
 * @param token - JWT access token.
 * @param plan - Plan tier to subscribe to (default "starter").
 */
export async function subscribeUserAPI(token: string, plan = "starter") {
  const res = await fetch(`${API_BASE}/api/v1/subscriptions/checkout`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ plan }),
  });
  if (!res.ok) throw new Error(`Subscribe failed: ${res.status} ${await res.text()}`);
  return await res.json();
}

// ---------------------------------------------------------------------------
// Phase 1 feature helpers — create test data via backend API
// ---------------------------------------------------------------------------

/**
 * Generic POST helper with retry logic for transient 401/404 errors.
 *
 * @param token - JWT access token.
 * @param path - API path (e.g. "/api/v1/stores/{id}/discounts").
 * @param body - Request body object.
 * @returns The parsed JSON response.
 */
async function apiPost(token: string, path: string, body: unknown) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });
    if (res.ok) return await res.json();
    // Retry on 400 as well — transient race conditions (e.g. "Parent category
    // not found") can occur when a prior request's commit hasn't propagated yet.
    if ((res.status === 400 || res.status === 401 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 300));
      continue;
    }
    throw new Error(`API POST ${path} failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Create a discount via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param overrides - Optional field overrides.
 * @returns The created discount object.
 */
export async function createDiscountAPI(
  token: string,
  storeId: string,
  overrides: Record<string, unknown> = {}
) {
  return apiPost(token, `/api/v1/stores/${storeId}/discounts`, {
    code: `SAVE${Date.now().toString(36).toUpperCase()}`,
    discount_type: "percentage",
    value: 10,
    starts_at: new Date().toISOString(),
    ...overrides,
  });
}

/**
 * Create a category via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param name - Category name.
 * @param parentId - Optional parent category ID for nesting.
 * @returns The created category object.
 */
export async function createCategoryAPI(
  token: string,
  storeId: string,
  name?: string,
  parentId?: string
) {
  return apiPost(token, `/api/v1/stores/${storeId}/categories`, {
    name: name || `Category ${Date.now()}`,
    ...(parentId ? { parent_id: parentId } : {}),
  });
}

/**
 * Create a supplier via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param overrides - Optional field overrides.
 * @returns The created supplier object.
 */
export async function createSupplierAPI(
  token: string,
  storeId: string,
  overrides: Record<string, unknown> = {}
) {
  return apiPost(token, `/api/v1/stores/${storeId}/suppliers`, {
    name: `Supplier ${Date.now()}`,
    contact_email: `supplier-${Date.now()}@example.com`,
    ...overrides,
  });
}

/**
 * Create a tax rate via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param overrides - Optional field overrides.
 * @returns The created tax rate object.
 */
export async function createTaxRateAPI(
  token: string,
  storeId: string,
  overrides: Record<string, unknown> = {}
) {
  return apiPost(token, `/api/v1/stores/${storeId}/tax-rates`, {
    name: "Sales Tax",
    rate: 8.25,
    country: "US",
    ...overrides,
  });
}

/**
 * Create a gift card via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param initialBalance - Starting balance (default 50).
 * @returns The created gift card object.
 */
export async function createGiftCardAPI(
  token: string,
  storeId: string,
  initialBalance = 50
) {
  return apiPost(token, `/api/v1/stores/${storeId}/gift-cards`, {
    initial_balance: initialBalance,
  });
}

/**
 * Create a webhook via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @returns The created webhook object.
 */
export async function createWebhookAPI(token: string, storeId: string) {
  return apiPost(token, `/api/v1/stores/${storeId}/webhooks`, {
    url: "https://hooks.example.com/test",
    events: ["order.created", "order.updated"],
  });
}

/**
 * Invite a team member via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param email - Invite email.
 * @returns The created invite object.
 */
export async function inviteTeamMemberAPI(
  token: string,
  storeId: string,
  email?: string
) {
  return apiPost(token, `/api/v1/stores/${storeId}/team/invite`, {
    email: email || uniqueEmail(),
    role: "editor",
  });
}

/**
 * Create a customer segment via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param name - Segment name.
 * @param overrides - Optional field overrides (e.g. description, segment_type).
 * @returns The created segment object.
 */
export async function createSegmentAPI(
  token: string,
  storeId: string,
  name?: string,
  overrides: Record<string, unknown> = {}
) {
  return apiPost(token, `/api/v1/stores/${storeId}/segments`, {
    name: name || `Segment ${Date.now()}`,
    description: "Test segment for e2e",
    segment_type: "manual",
    ...overrides,
  });
}

/**
 * Create an upsell via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param sourceProductId - Source product UUID.
 * @param targetProductId - Target product UUID.
 * @returns The created upsell object.
 */
export async function createUpsellAPI(
  token: string,
  storeId: string,
  sourceProductId: string,
  targetProductId: string
) {
  return apiPost(token, `/api/v1/stores/${storeId}/upsells`, {
    source_product_id: sourceProductId,
    target_product_id: targetProductId,
    upsell_type: "cross_sell",
    position: 1,
  });
}

/**
 * Create an A/B test via the API.
 *
 * @param token - JWT access token.
 * @param storeId - The store UUID.
 * @param overrides - Optional field overrides.
 * @returns The created A/B test object.
 */
export async function createABTestAPI(
  token: string,
  storeId: string,
  overrides: Record<string, unknown> = {}
) {
  return apiPost(token, `/api/v1/stores/${storeId}/ab-tests`, {
    name: `Test ${Date.now()}`,
    metric: "conversion_rate",
    variants: [
      { name: "Control", weight: 50 },
      { name: "Variant A", weight: 50 },
    ],
    ...overrides,
  });
}

/**
 * Generic PATCH helper with retry logic for transient 401/404 errors.
 *
 * @param token - JWT access token.
 * @param path - API path.
 * @param body - Request body object.
 * @returns The parsed JSON response.
 */
async function apiPatch(token: string, path: string, body: unknown) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });
    if (res.ok) return await res.json();
    if ((res.status === 401 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 200));
      continue;
    }
    throw new Error(`API PATCH ${path} failed: ${res.status} ${await res.text()}`);
  }
}

/** Default shipping address for test orders. */
export const TEST_SHIPPING_ADDRESS = {
  name: "Test User",
  line1: "123 Test Street",
  city: "Testville",
  state: "CA",
  postal_code: "90210",
  country: "US",
};

/**
 * Create an order via the public checkout API (no auth needed).
 *
 * @param slug - Store slug.
 * @param customerEmail - Customer email.
 * @param items - Cart items with product_id, variant_id, quantity.
 * @param shippingAddress - Optional shipping address override.
 * @returns The checkout response with order_id.
 */
export async function createOrderAPI(
  slug: string,
  customerEmail: string,
  items: { product_id: string; variant_id?: string; quantity: number }[],
  shippingAddress?: Record<string, string>
) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${API_BASE}/api/v1/public/stores/${slug}/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_email: customerEmail,
        items,
        shipping_address: shippingAddress || TEST_SHIPPING_ADDRESS,
      }),
    });
    if (res.ok) return await res.json();
    if ((res.status === 400 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 300));
      continue;
    }
    throw new Error(`Checkout failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Update an order's status via the API.
 *
 * @param token - JWT access token.
 * @param storeId - Store UUID.
 * @param orderId - Order UUID.
 * @param status - New status (e.g. "paid", "shipped", "delivered").
 * @returns The updated order object.
 */
export async function updateOrderStatusAPI(
  token: string,
  storeId: string,
  orderId: string,
  status: string
) {
  return apiPatch(token, `/api/v1/stores/${storeId}/orders/${orderId}`, { status });
}

/**
 * Link a supplier to a product via the API.
 *
 * @param token - JWT access token.
 * @param storeId - Store UUID.
 * @param productId - Product UUID.
 * @param supplierId - Supplier UUID.
 * @param supplierCost - Cost per unit from the supplier.
 * @returns The created product-supplier link.
 */
export async function linkProductSupplierAPI(
  token: string,
  storeId: string,
  productId: string,
  supplierId: string,
  supplierCost: number
) {
  return apiPost(token, `/api/v1/stores/${storeId}/products/${productId}/suppliers`, {
    supplier_id: supplierId,
    supplier_cost: supplierCost,
    is_primary: true,
  });
}

/**
 * Generic GET helper with retry logic for transient 401/404 errors.
 *
 * @param token - JWT access token.
 * @param path - API path.
 * @returns The parsed JSON response.
 */
export async function apiGet(token: string, path: string) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) return await res.json();
    if ((res.status === 401 || res.status === 404) && attempt < 4) {
      await new Promise((r) => setTimeout(r, 200));
      continue;
    }
    throw new Error(`API GET ${path} failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Create a refund via the API.
 *
 * The backend ``reason`` column is an enum with values: ``defective``,
 * ``wrong_item``, ``not_as_described``, ``changed_mind``, ``other``.
 * Free-text reasons that do not match an enum value are mapped to ``other``.
 * Use ``reason_details`` for a human-readable explanation.
 *
 * @param token - JWT access token.
 * @param storeId - Store UUID.
 * @param orderId - Order UUID to refund.
 * @param amount - Refund amount.
 * @param reason - Refund reason enum value (default "defective").
 * @param reasonDetails - Optional free-text elaboration.
 * @returns The created refund object.
 */
export async function createRefundAPI(
  token: string,
  storeId: string,
  orderId: string,
  amount: number,
  reason = "defective",
  reasonDetails?: string
) {
  return apiPost(token, `/api/v1/stores/${storeId}/refunds`, {
    order_id: orderId,
    amount,
    reason,
    ...(reasonDetails ? { reason_details: reasonDetails } : {}),
  });
}

/**
 * Create a review via the public storefront API.
 *
 * The reviews POST endpoint is only available on the public storefront
 * path: ``/api/v1/public/stores/{slug}/products/{product_slug}/reviews``.
 * There is no admin POST for reviews.
 *
 * @param token - JWT access token (used to resolve store slug).
 * @param storeId - Store UUID (used to resolve store slug).
 * @param productId - Product UUID (used to resolve product slug).
 * @param overrides - Optional field overrides (rating, title, body,
 *   customer_name, customer_email).
 * @returns The created review object.
 */
export async function createReviewAPI(
  token: string,
  storeId: string,
  productId: string,
  overrides: Record<string, unknown> = {}
) {
  // Resolve store slug from storeId
  const storeData = await apiGet(token, `/api/v1/stores/${storeId}`);
  const storeSlug = storeData.slug;

  // Resolve product slug from productId
  const productData = await apiGet(token, `/api/v1/stores/${storeId}/products/${productId}`);
  const productSlug = productData.slug;

  // Map the helper's field names to what the public CreateReviewRequest expects.
  // The schema uses customer_name / customer_email (not reviewer_name / reviewer_email).
  const reviewerName = (overrides.reviewer_name ?? overrides.customer_name ?? "Test User") as string;
  const reviewerEmail = (overrides.reviewer_email ?? overrides.customer_email ?? `reviewer-${Date.now()}@test.com`) as string;

  // POST to the public review endpoint (no auth required)
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${API_BASE}/api/v1/public/stores/${storeSlug}/products/${productSlug}/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rating: (overrides.rating as number) ?? 5,
        title: (overrides.title as string) ?? "Great product",
        body: (overrides.body as string) ?? "Highly recommended!",
        customer_name: reviewerName,
        customer_email: reviewerEmail,
      }),
    });
    if (res.ok) return await res.json();
    if (res.status === 404 && attempt < 4) {
      await new Promise((r) => setTimeout(r, 200));
      continue;
    }
    throw new Error(`Create review failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Register a customer account on a storefront via the API.
 *
 * @param slug - Store slug.
 * @param email - Customer email.
 * @param password - Customer password (min 6 chars).
 * @param firstName - Customer first name.
 * @param lastName - Customer last name.
 * @returns The registration response with access_token and customer data.
 */
export async function registerCustomerAPI(
  slug: string,
  email: string,
  password: string,
  firstName = "Test",
  lastName = "Customer"
) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${API_BASE}/api/v1/public/stores/${slug}/customers/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        password,
        first_name: firstName,
        last_name: lastName,
      }),
    });
    if (res.ok) return await res.json();
    if (res.status === 404 && attempt < 4) {
      await new Promise((r) => setTimeout(r, 300));
      continue;
    }
    throw new Error(`Customer register failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Login a customer on a storefront via the API.
 *
 * @param slug - Store slug.
 * @param email - Customer email.
 * @param password - Customer password.
 * @returns The login response with access_token.
 */
export async function loginCustomerAPI(
  slug: string,
  email: string,
  password: string
) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(`${API_BASE}/api/v1/public/stores/${slug}/customers/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (res.ok) return await res.json();
    if (res.status === 404 && attempt < 4) {
      await new Promise((r) => setTimeout(r, 300));
      continue;
    }
    throw new Error(`Customer login failed: ${res.status} ${await res.text()}`);
  }
}

/**
 * Mark an order as shipped with tracking information via the API.
 *
 * @param token - Store owner JWT access token.
 * @param storeId - Store UUID.
 * @param orderId - Order UUID.
 * @param trackingNumber - Tracking number string.
 * @param carrier - Optional carrier name.
 * @returns The updated order response.
 */
export async function fulfillOrderAPI(
  token: string,
  storeId: string,
  orderId: string,
  trackingNumber: string,
  carrier?: string
) {
  return apiPost(token, `/api/v1/stores/${storeId}/orders/${orderId}/fulfill`, {
    tracking_number: trackingNumber,
    carrier: carrier || null,
  });
}

/**
 * Mark a shipped order as delivered via the API.
 *
 * @param token - Store owner JWT access token.
 * @param storeId - Store UUID.
 * @param orderId - Order UUID.
 * @returns The updated order response.
 */
export async function deliverOrderAPI(
  token: string,
  storeId: string,
  orderId: string
) {
  return apiPost(token, `/api/v1/stores/${storeId}/orders/${orderId}/deliver`, {});
}

/**
 * Run the seed script to populate the database with demo data.
 *
 * The seed script is idempotent — re-running it skips already-created
 * entities (409 conflicts). Safe to call multiple times.
 *
 * @returns An object with the seed user token and store data.
 */
export async function seedDatabase(): Promise<{
  token: string;
  storeId: string;
  storeSlug: string;
}> {
  // Helper to login as seed user with retries
  async function loginSeed(): Promise<string | null> {
    for (let i = 0; i < 10; i++) {
      try {
        const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: "demo@example.com", password: "password123" }),
        });
        if (res.ok) return (await res.json()).access_token;
        if (res.status === 401 || res.status === 400) return null;
      } catch {
        // Server not ready — retry
      }
      await new Promise((r) => setTimeout(r, 500));
    }
    return null;
  }

  let token = await loginSeed();

  if (!token) {
    // User doesn't exist yet — run the seed script
    const { execSync } = await import("child_process");
    execSync("npx tsx /workspaces/ecomm/scripts/seed.ts", {
      cwd: "/workspaces/ecomm",
      timeout: 120000,
      stdio: "pipe",
    });
    // Wait for backend to stabilize after heavy writes
    await new Promise((r) => setTimeout(r, 2000));
    token = await loginSeed();
    if (!token) throw new Error("Seed login failed after running seed script");
  }

  await waitForToken(token);

  // Get the seed store with retries
  for (let i = 0; i < 5; i++) {
    try {
      const storesRes = await fetch(`${API_BASE}/api/v1/stores`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (storesRes.ok) {
        const stores = await storesRes.json();
        const storeList = Array.isArray(stores) ? stores : stores.items ?? stores;
        const store = storeList.find((s: any) => s.slug === "volt-electronics") || storeList[0];
        if (store) return { token, storeId: store.id, storeSlug: store.slug };
      }
    } catch {
      // Retry
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("No seed store found");
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
