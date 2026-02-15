/**
 * Authentication token management factory.
 *
 * Creates a namespaced auth manager bound to a service slug. All storage
 * keys are prefixed with the slug to prevent collisions when multiple
 * dashboards run on the same domain (e.g. localhost during development).
 *
 * **For Developers:**
 *   - Call `createAuthManager(slug)` once in your service config.
 *   - The returned object provides getToken, setToken, clearToken,
 *     isAuthenticated, setUserEmail, getUserEmail, and logout.
 *   - `isAuthenticated()` is a quick sync check; it does NOT validate
 *     the token server-side — that happens on each API call.
 *
 * **For QA Engineers:**
 *   - Clearing localStorage will log the user out on next navigation.
 *   - An expired token triggers a 401 from the API, which the api client
 *     handles by redirecting to /login.
 *   - Verify that logging out fully clears the token.
 *
 * **For End Users:**
 *   - You are automatically logged out when your session expires.
 *   - Clicking "Log out" immediately ends your session.
 */

/**
 * Auth manager interface returned by createAuthManager.
 *
 * For Developers:
 *   All functions are bound to the service slug for namespaced storage.
 */
export interface AuthManager {
  /** Retrieve the stored JWT access token, or null if none. */
  getToken: () => string | null;
  /** Store a JWT access token in localStorage. */
  setToken: (token: string) => void;
  /** Remove the stored JWT token and email from localStorage. */
  clearToken: () => void;
  /** Quick sync check for whether a token exists (no server validation). */
  isAuthenticated: () => boolean;
  /** Store the authenticated user's email for display in the UI. */
  setUserEmail: (email: string) => void;
  /** Retrieve the stored user email, or null. */
  getUserEmail: () => string | null;
  /** Clear all auth state and redirect to /login. */
  logout: () => void;
}

/**
 * Create a namespaced auth manager for a specific service.
 *
 * @param slug - The service slug used to namespace localStorage keys.
 * @returns An AuthManager object with all token management functions.
 *
 * @example
 * const auth = createAuthManager("trendscout");
 * auth.setToken(response.access_token);
 * if (auth.isAuthenticated()) { ... }
 */
export function createAuthManager(slug: string): AuthManager {
  const TOKEN_KEY = `${slug}_auth_token`;
  const EMAIL_KEY = `${slug}_user_email`;

  function getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(TOKEN_KEY);
  }

  function setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  }

  function clearToken(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
  }

  function isAuthenticated(): boolean {
    return getToken() !== null;
  }

  function setUserEmail(email: string): void {
    localStorage.setItem(EMAIL_KEY, email);
  }

  function getUserEmail(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(EMAIL_KEY);
  }

  function logout(): void {
    clearToken();
    window.location.href = "/login";
  }

  return {
    getToken,
    setToken,
    clearToken,
    isAuthenticated,
    setUserEmail,
    getUserEmail,
    logout,
  };
}
