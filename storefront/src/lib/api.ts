/**
 * Storefront API client.
 *
 * Lightweight fetch wrapper for the customer-facing storefront to communicate
 * with the backend's public endpoints. Unlike the dashboard client, this does
 * not include JWT authentication since storefront requests are unauthenticated.
 *
 * All responses are normalized into `{ data, error }` for uniform handling.
 */

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

/**
 * Send an HTTP request and return a normalized response.
 * @param path - API path (e.g. "/api/v1/public/stores/my-store").
 * @param options - Additional fetch options (method, body, headers).
 * @returns An ApiResponse with either data or error populated.
 */
async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

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

/** Pre-configured API client with get and post methods. */
export const api = {
  /**
   * Send a GET request.
   * @param path - API path to fetch.
   */
  get: <T>(path: string) => request<T>(path),

  /**
   * Send a POST request with a JSON body.
   * @param path - API path to post to.
   * @param body - Request payload (will be JSON-serialized).
   */
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
};
