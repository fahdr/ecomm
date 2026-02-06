/**
 * Store resolution utilities for the storefront.
 *
 * Handles fetching store data from the backend public API and extracting
 * the store slug from either a query parameter (local dev) or subdomain
 * (production).
 *
 * **For Developers:**
 *   - Local dev: pass ``?store=my-slug`` in the URL.
 *   - Production: the slug is extracted from the first subdomain segment
 *     (e.g. ``my-slug.platform.com``).
 *   - The ``STOREFRONT_DOMAIN`` env var controls subdomain extraction.
 *
 * **For QA Engineers:**
 *   - If no slug can be resolved, pages should show a "Store not found" state.
 *   - Only active stores return data; paused/deleted return null.
 */

import { api } from "./api";
import type { Store } from "./types";

/**
 * The root domain used in production for subdomain-based store resolution.
 * Not needed for local development where query params are used.
 */
const STOREFRONT_DOMAIN = process.env.STOREFRONT_DOMAIN || "";

/**
 * Extract the store slug from a request URL.
 *
 * In local development, reads the ``store`` query parameter.
 * In production, extracts the first subdomain segment from the hostname.
 *
 * @param url - The full request URL.
 * @returns The store slug, or null if it cannot be resolved.
 *
 * @example
 * // Local dev
 * resolveSlug("http://localhost:3001?store=my-store") // => "my-store"
 *
 * // Production
 * resolveSlug("https://my-store.platform.com/") // => "my-store"
 */
export function resolveSlug(url: string): string | null {
  const parsed = new URL(url);

  // Local dev: use ?store= query param
  const querySlug = parsed.searchParams.get("store");
  if (querySlug) {
    return querySlug;
  }

  // Production: extract subdomain
  if (STOREFRONT_DOMAIN && parsed.hostname.endsWith(STOREFRONT_DOMAIN)) {
    const subdomain = parsed.hostname.replace(`.${STOREFRONT_DOMAIN}`, "");
    if (subdomain && subdomain !== parsed.hostname) {
      return subdomain;
    }
  }

  return null;
}

/**
 * Fetch store data from the backend public API by slug.
 *
 * @param slug - The store slug to look up.
 * @returns The Store data if found and active, or null otherwise.
 */
export async function fetchStore(slug: string): Promise<Store | null> {
  const { data, error } = await api.get<Store>(
    `/api/v1/public/stores/${encodeURIComponent(slug)}`
  );

  if (error || !data) {
    return null;
  }

  return data;
}
