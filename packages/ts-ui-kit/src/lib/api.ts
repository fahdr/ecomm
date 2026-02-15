/**
 * HTTP API client for communicating with service backends.
 *
 * Wraps the native fetch API with JSON serialization, JWT authentication,
 * and error normalization. All responses use a `{ data, error }` envelope
 * so callers can handle success and failure uniformly without try/catch.
 *
 * **For Developers:**
 *   - Instantiate with `new ApiClient(baseUrl, authManager)`.
 *   - The auth manager provides getToken/clearToken for JWT lifecycle.
 *   - On 401 responses, the client automatically redirects to /login.
 *   - The `get`, `post`, `patch`, `del` methods are generic for type safety.
 *
 * **For QA Engineers:**
 *   - Check Network tab to verify Authorization header is sent.
 *   - Verify 401 auto-redirect works by manually expiring the token.
 *   - Test with the API server down to verify error messages.
 *
 * **For End Users:**
 *   - If you see a "Session expired" message, simply log in again.
 */

import type { AuthManager } from "./auth";

/**
 * Normalized API response envelope.
 * Every API call returns this shape, making error handling consistent.
 *
 * @template T - The type of the data payload on success.
 */
export interface ApiResponse<T> {
  /** The response data on success, or null on error. */
  data: T | null;
  /** The error details on failure, or null on success. */
  error: { code: string; message: string } | null;
}

/**
 * HTTP client class with JWT auth, JSON serialization, and error normalization.
 *
 * For Developers:
 *   Accepts a base URL and auth manager at construction. All requests
 *   automatically attach the Bearer token and handle 401 redirects.
 *
 * @example
 * const api = new ApiClient("http://localhost:8101", authManager);
 * const { data, error } = await api.get<User[]>("/api/v1/users");
 */
export class ApiClient {
  private baseUrl: string;
  private auth: AuthManager;

  /**
   * @param baseUrl - The root URL of the backend API.
   * @param auth - Auth manager for token retrieval and clearance.
   */
  constructor(baseUrl: string, auth: AuthManager) {
    this.baseUrl = baseUrl;
    this.auth = auth;
  }

  /**
   * Internal request method that handles headers, auth, serialization, and errors.
   *
   * @param path - API path relative to baseUrl.
   * @param options - Standard fetch RequestInit options.
   * @returns Normalized ApiResponse with either data or error.
   */
  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    const token = this.auth.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...options,
        headers,
      });

      /* Auto-redirect to login on authentication failure */
      if (response.status === 401) {
        this.auth.clearToken();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        return {
          data: null,
          error: { code: "401", message: "Session expired. Please log in again." },
        };
      }

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        return {
          data: null,
          error: {
            code: String(response.status),
            message: errorBody.detail || errorBody.message || response.statusText,
          },
        };
      }

      /* Handle 204 No Content (e.g. DELETE responses) */
      if (response.status === 204) {
        return { data: null as unknown as T, error: null };
      }

      const data = await response.json();
      return { data, error: null };
    } catch (err) {
      return {
        data: null,
        error: {
          code: "NETWORK_ERROR",
          message: err instanceof Error ? err.message : "Network request failed",
        },
      };
    }
  }

  /**
   * Send a GET request.
   * @param path - API endpoint path.
   */
  get<T>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>(path);
  }

  /**
   * Send a POST request with a JSON body.
   * @param path - API endpoint path.
   * @param body - Request payload (will be JSON-serialized).
   */
  post<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  /**
   * Send a PATCH request with a JSON body.
   * @param path - API endpoint path.
   * @param body - Partial update payload (will be JSON-serialized).
   */
  patch<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  /**
   * Send a PUT request with a JSON body.
   * @param path - API endpoint path.
   * @param body - Request payload (will be JSON-serialized).
   */
  put<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  /**
   * Send a DELETE request.
   * @param path - API endpoint path.
   */
  del<T>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>(path, { method: "DELETE" });
  }
}
