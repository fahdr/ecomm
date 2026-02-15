/**
 * Authentication token management utilities.
 *
 * Uses localStorage for token persistence. Tokens are stored as plain
 * JWT strings and attached to API requests via the api client.
 *
 * **For Developers:**
 *   - `getToken()` / `setToken()` / `clearToken()` manage the JWT in localStorage.
 *   - `isAuthenticated()` is a quick sync check; it does NOT validate the token
 *     server-side — that happens on each API call.
 *   - `logout()` clears all auth state and redirects to /login.
 *   - The token key includes the service slug to avoid collisions when multiple
 *     service dashboards run on the same domain (e.g. localhost during dev).
 *
 * **For QA Engineers:**
 *   - Clearing localStorage will log the user out on next navigation.
 *   - An expired token will trigger a 401 from the API, which the api client
 *     handles by redirecting to /login.
 *   - Verify that logging out fully clears the token (check Application > Local Storage).
 *
 * **For End Users:**
 *   - You are automatically logged out when your session expires.
 *   - Clicking "Log out" in the sidebar immediately ends your session.
 */

import { serviceConfig } from "@/service.config";

/** Storage key, namespaced by service slug to avoid cross-service collisions. */
const TOKEN_KEY = `${serviceConfig.slug}_auth_token`;

/** Storage key for the authenticated user's email address. */
const EMAIL_KEY = `${serviceConfig.slug}_user_email`;

/**
 * Retrieve the stored JWT access token.
 *
 * @returns The JWT string, or null if no token is stored.
 */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Store a JWT access token in localStorage.
 *
 * @param token - The JWT string received from the login/register API response.
 */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Remove the stored JWT token from localStorage.
 */
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EMAIL_KEY);
}

/**
 * Quick synchronous check for whether a token exists.
 * Does NOT validate the token server-side.
 *
 * @returns True if a token string is present in localStorage.
 */
export function isAuthenticated(): boolean {
  return getToken() !== null;
}

/**
 * Store the authenticated user's email for display in the UI.
 *
 * @param email - The user's email address.
 */
export function setUserEmail(email: string): void {
  localStorage.setItem(EMAIL_KEY, email);
}

/**
 * Retrieve the stored user email.
 *
 * @returns The email string, or null if not stored.
 */
export function getUserEmail(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(EMAIL_KEY);
}

/**
 * Fully log out the user: clear all stored auth state and redirect to /login.
 * This is the primary logout mechanism used by the sidebar and top bar.
 */
export function logout(): void {
  clearToken();
  window.location.href = "/login";
}
