/**
 * Storefront API client.
 *
 * Lightweight fetch wrapper for the customer-facing storefront to communicate
 * with the backend's public endpoints. Supports optional JWT authentication
 * for customer account operations (orders, wishlist, profile).
 *
 * All responses are normalized into ``{ data, error }`` for uniform handling.
 *
 * **For Developers:**
 *   - Use ``api.get`` / ``api.post`` / ``api.patch`` / ``api.del`` for requests.
 *   - Pass an ``authToken`` in the options to attach a Bearer header.
 *   - The ``204 No Content`` response is handled gracefully (returns null data).
 *
 * **For QA Engineers:**
 *   - All HTTP errors are caught and returned in the ``error`` field.
 *   - Network errors are surfaced as ``{ code: "NETWORK", message: "..." }``.
 */

import { getCustomerAccessToken } from "./auth";

/** Base URL for the backend API, configurable via environment variable. */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Standard API response envelope.
 * @template T - The type of the data payload on success.
 */
interface ApiResponse<T> {
  data: T | null;
  error: { code: string; message: string } | null;
}

/** Extended fetch options with optional auth token. */
interface RequestOptions extends RequestInit {
  /** JWT token to attach as a Bearer header. If omitted, uses stored customer token. */
  authToken?: string | null;
  /** Skip auto-attaching customer token (for public endpoints). */
  noAuth?: boolean;
}

/**
 * Send an HTTP request and return a normalized response.
 *
 * @param path - API path (e.g. "/api/v1/public/stores/my-store").
 * @param options - Additional fetch options (method, body, headers, authToken).
 * @returns An ApiResponse with either data or error populated.
 */
async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> {
  const { authToken, noAuth, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOptions.headers as Record<string, string>),
  };

  // Attach Bearer token: explicit authToken > stored customer token
  const token = authToken ?? (noAuth ? null : getCustomerAccessToken());
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...fetchOptions,
    headers,
  });

  // Handle 204 No Content
  if (response.status === 204) {
    return { data: null, error: null };
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    return {
      data: null,
      error: {
        code: String(response.status),
        message: errorBody.detail || response.statusText,
      },
    };
  }

  const data = await response.json();
  return { data, error: null };
}

/** Pre-configured API client with HTTP method helpers. */
export const api = {
  /**
   * Send a GET request.
   *
   * @param path - API path to fetch.
   * @param options - Optional request options.
   */
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, options),

  /**
   * Send a POST request with a JSON body.
   *
   * @param path - API path to post to.
   * @param body - Request payload (will be JSON-serialized).
   * @param options - Optional request options.
   */
  post: <T>(path: string, body: unknown, options?: RequestOptions) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body), ...options }),

  /**
   * Send a PATCH request with a JSON body.
   *
   * @param path - API path to patch.
   * @param body - Partial update payload.
   * @param options - Optional request options.
   */
  patch: <T>(path: string, body: unknown, options?: RequestOptions) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body), ...options }),

  /**
   * Send a DELETE request.
   *
   * @param path - API path to delete.
   * @param options - Optional request options.
   */
  del: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { method: "DELETE", ...options }),
};
