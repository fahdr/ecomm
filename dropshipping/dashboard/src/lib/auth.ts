/**
 * Authentication token helpers.
 *
 * Provides functions to store, retrieve, and clear JWT tokens using browser
 * cookies. Cookies are used (instead of localStorage) so that Next.js
 * middleware can check authentication status on the server side.
 *
 * **For Developers:**
 *   - Access tokens are stored with a 15-minute expiry.
 *   - Refresh tokens are stored with a 7-day expiry.
 *   - Both cookies use `path=/` and `SameSite=Lax`.
 *
 * **For QA Engineers:**
 *   - Clearing cookies (via browser dev tools) will log the user out on next
 *     navigation because middleware will redirect to `/login`.
 */

/** Cookie name for the short-lived access token. */
const ACCESS_TOKEN_KEY = "access_token";

/** Cookie name for the long-lived refresh token. */
const REFRESH_TOKEN_KEY = "refresh_token";

/**
 * Set a cookie with the given name, value, and max-age in seconds.
 *
 * @param name - Cookie name.
 * @param value - Cookie value.
 * @param maxAgeSeconds - Time-to-live in seconds.
 */
function setCookie(name: string, value: string, maxAgeSeconds: number): void {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSeconds}; SameSite=Lax`;
}

/**
 * Read a cookie value by name.
 *
 * @param name - Cookie name to look up.
 * @returns The decoded cookie value, or null if not found.
 */
function getCookie(name: string): string | null {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=")[1]) : null;
}

/**
 * Delete a cookie by setting its max-age to 0.
 *
 * @param name - Cookie name to delete.
 */
function deleteCookie(name: string): void {
  document.cookie = `${name}=; path=/; max-age=0`;
}

/**
 * Store both access and refresh tokens as cookies.
 *
 * @param accessToken - The JWT access token (15-minute expiry).
 * @param refreshToken - The JWT refresh token (7-day expiry).
 */
export function setTokens(accessToken: string, refreshToken: string): void {
  setCookie(ACCESS_TOKEN_KEY, accessToken, 15 * 60); // 15 minutes
  setCookie(REFRESH_TOKEN_KEY, refreshToken, 7 * 24 * 60 * 60); // 7 days
}

/**
 * Retrieve the stored access token.
 *
 * @returns The access token string, or null if not set.
 */
export function getAccessToken(): string | null {
  return getCookie(ACCESS_TOKEN_KEY);
}

/**
 * Retrieve the stored refresh token.
 *
 * @returns The refresh token string, or null if not set.
 */
export function getRefreshToken(): string | null {
  return getCookie(REFRESH_TOKEN_KEY);
}

/**
 * Clear both access and refresh token cookies, effectively logging out.
 */
export function clearTokens(): void {
  deleteCookie(ACCESS_TOKEN_KEY);
  deleteCookie(REFRESH_TOKEN_KEY);
}
