/**
 * HTTP API client for communicating with the service backend.
 *
 * Wraps the native fetch API with JSON serialization, JWT authentication,
 * and error normalization. All responses use a `{ data, error }` envelope
 * so callers can handle success and failure uniformly without try/catch.
 *
 * **For Developers:**
 *   - The base URL comes from `serviceConfig.apiUrl` (set via NEXT_PUBLIC_API_URL).
 *   - Call `api.setToken()` after login to attach the Bearer token to every request.
 *   - On 401 responses, the client automatically redirects to /login.
 *   - The `get`, `post`, `patch`, `del` methods are generic for type safety.
 *
 * **For QA Engineers:**
 *   - Check Network tab to verify Authorization header is sent on authenticated requests.
 *   - Verify 401 auto-redirect works by manually expiring the token.
 *   - Test with the API server down to verify error messages are shown.
 *
 * **For End Users:**
 *   - If you see a "Session expired" message, simply log in again.
 */

import { serviceConfig } from "@/service.config";
import { getToken, clearToken } from "@/lib/auth";

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
 * @example
 * const { data, error } = await api.get<User[]>("/api/v1/users");
 * if (error) console.error(error.message);
 * else console.log(data);
 */
class ApiClient {
  private baseUrl: string;

  /**
   * @param baseUrl - The root URL of the backend API (e.g. "http://localhost:8001").
   */
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * Internal request method that handles headers, auth, serialization, and errors.
   *
   * @param path - API path relative to baseUrl (e.g. "/api/v1/billing/overview").
   * @param options - Standard fetch RequestInit options (method, body, headers).
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

    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...options,
        headers,
      });

      /* Auto-redirect to login on authentication failure (except on login page itself) */
      if (response.status === 401) {
        const isLoginPage = typeof window !== "undefined" && window.location.pathname.includes("/login");
        if (!isLoginPage) {
          clearToken();
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
          return {
            data: null,
            error: { code: "401", message: "Session expired. Please log in again." },
          };
        }
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
   * Send a DELETE request.
   * @param path - API endpoint path.
   */
  del<T>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>(path, { method: "DELETE" });
  }
}

/**
 * Pre-configured API client instance pointing to the service backend.
 * Import and use directly: `import { api } from "@/lib/api"`
 */
export const api = new ApiClient(serviceConfig.apiUrl);
