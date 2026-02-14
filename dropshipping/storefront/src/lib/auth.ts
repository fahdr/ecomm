/**
 * Customer authentication token management for the storefront.
 *
 * Handles storage and retrieval of customer JWT tokens using localStorage.
 * Tokens are namespaced with ``customer_`` to avoid conflicts with any
 * dashboard tokens.
 *
 * **For Developers:**
 *   Call ``setCustomerTokens()`` after login/register, and
 *   ``getCustomerAccessToken()`` when making authenticated API calls.
 *   ``clearCustomerTokens()`` on logout.
 *
 * **For QA Engineers:**
 *   - Tokens are stored in localStorage under ``customer_access_token``
 *     and ``customer_refresh_token``.
 *   - ``clearCustomerTokens()`` removes both tokens.
 */

const ACCESS_TOKEN_KEY = "customer_access_token";
const REFRESH_TOKEN_KEY = "customer_refresh_token";

/**
 * Store customer tokens in localStorage.
 *
 * @param accessToken - The JWT access token.
 * @param refreshToken - The JWT refresh token.
 */
export function setCustomerTokens(
  accessToken: string,
  refreshToken: string
): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

/**
 * Retrieve the customer access token from localStorage.
 *
 * @returns The access token string, or null if not set.
 */
export function getCustomerAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * Retrieve the customer refresh token from localStorage.
 *
 * @returns The refresh token string, or null if not set.
 */
export function getCustomerRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

/**
 * Remove all customer tokens from localStorage (logout).
 */
export function clearCustomerTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}
