/**
 * Admin API client for the Super Admin Dashboard.
 *
 * Handles JWT-based authentication and provides typed methods for
 * communicating with the admin backend at http://localhost:8300.
 *
 * For Developers:
 *   Import `adminApi` and call methods like `adminApi.get("/health/services")`.
 *   The client automatically attaches the JWT from localStorage and
 *   handles 401 responses by redirecting to /login.
 *
 * For QA Engineers:
 *   Verify that expired tokens trigger a redirect to /login.
 *   Verify that the Authorization header is sent on every request.
 *
 * For Project Managers:
 *   This client is the single interface between the dashboard UI
 *   and the admin backend. All API calls flow through here.
 */

/** LocalStorage key for the admin JWT token. */
const TOKEN_KEY = "admin_token";

/** Base URL for the admin backend API. */
const BASE_URL =
  process.env.NEXT_PUBLIC_ADMIN_API_URL || "http://localhost:8300/api/v1/admin";

/**
 * Admin API client class.
 *
 * Stores JWT in localStorage, attaches it to all requests as a
 * Bearer token, and handles 401 responses by clearing the token
 * and redirecting to /login.
 */
class AdminApiClient {
  /**
   * Retrieve the stored JWT token.
   *
   * @returns The JWT string or null if not authenticated.
   */
  getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(TOKEN_KEY);
  }

  /**
   * Store a JWT token after successful authentication.
   *
   * @param token - The JWT string to persist.
   */
  setToken(token: string): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(TOKEN_KEY, token);
  }

  /**
   * Remove the stored JWT token (logout).
   */
  clearToken(): void {
    if (typeof window === "undefined") return;
    localStorage.removeItem(TOKEN_KEY);
  }

  /**
   * Check whether the user is authenticated (has a token).
   *
   * @returns True if a token exists in localStorage.
   */
  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  /**
   * Build HTTP headers for an API request.
   *
   * @returns Headers object with Content-Type and optional Authorization.
   */
  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }

  /**
   * Handle an API response, checking for auth failures.
   *
   * If the response is 401, the token is cleared and the user is
   * redirected to /login.
   *
   * @param response - The fetch Response object.
   * @returns The parsed JSON body.
   * @throws Error if the response indicates a non-auth failure.
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 401) {
      this.clearToken();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Unauthorized — redirecting to login");
    }

    if (response.status === 204) {
      return undefined as T;
    }

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(
        body.detail || body.message || `API error: ${response.status}`
      );
    }

    return response.json();
  }

  /**
   * Send a GET request to the admin API.
   *
   * @param path - The API path (e.g., "/health/services").
   * @returns The parsed response body.
   */
  async get<T = unknown>(path: string): Promise<T> {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: "GET",
      headers: this.getHeaders(),
    });
    return this.handleResponse<T>(response);
  }

  /**
   * Send a POST request to the admin API.
   *
   * @param path - The API path.
   * @param body - The JSON request body.
   * @returns The parsed response body.
   */
  async post<T = unknown>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response);
  }

  /**
   * Send a PATCH request to the admin API.
   *
   * @param path - The API path.
   * @param body - The JSON request body.
   * @returns The parsed response body.
   */
  async patch<T = unknown>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: "PATCH",
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response);
  }

  /**
   * Send a DELETE request to the admin API.
   *
   * @param path - The API path.
   * @returns The parsed response body (usually undefined for 204).
   */
  async delete<T = unknown>(path: string): Promise<T> {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
    return this.handleResponse<T>(response);
  }

  /**
   * Authenticate with the admin backend.
   *
   * @param email - Admin email address.
   * @param password - Admin password.
   * @returns The login response containing the JWT token.
   */
  async login(
    email: string,
    password: string
  ): Promise<{ access_token: string; admin: { email: string; name: string } }> {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || "Login failed");
    }

    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  /**
   * Run first-time admin setup (create the initial admin account).
   *
   * @param email - Admin email address.
   * @param password - Admin password.
   * @param name - Admin display name.
   * @returns The setup response containing the JWT token.
   */
  async setup(
    email: string,
    password: string,
    name: string
  ): Promise<{ access_token: string; admin: { email: string; name: string } }> {
    const response = await fetch(`${BASE_URL}/auth/setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name }),
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || "Setup failed");
    }

    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  /**
   * Log out the current admin user.
   *
   * Clears the stored token and redirects to /login.
   */
  logout(): void {
    this.clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }
}

/** Singleton instance of the admin API client. */
export const adminApi = new AdminApiClient();
