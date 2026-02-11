/**
 * Dashboard API client.
 *
 * Provides a typed fetch wrapper for communicating with the FastAPI backend.
 * Supports JWT authentication — call `api.setToken()` after login to attach
 * the Bearer token to every subsequent request.
 *
 * All responses are normalized into `{ data, error }` so callers can handle
 * success and failure uniformly without try/catch.
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
 * HTTP client class that manages base URL and auth token state.
 * Wraps the native fetch API with JSON serialization and error normalization.
 */
class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  /**
   * @param baseUrl - The root URL of the backend API (e.g. "http://localhost:8000").
   */
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * Set or clear the JWT token used for authenticated requests.
   * @param token - A valid JWT string, or null to clear authentication.
   */
  setToken(token: string | null) {
    this.token = token;
  }

  /**
   * Send an HTTP request and return a normalized response.
   * @param path - API path (e.g. "/api/v1/health").
   * @param options - Additional fetch options (method, body, headers).
   * @returns An ApiResponse with either data or error populated.
   */
  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
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

    // Handle 204 No Content (e.g. DELETE responses with empty body)
    if (response.status === 204) {
      return { data: null as unknown as T, error: null };
    }

    const data = await response.json();
    return { data, error: null };
  }

  /**
   * Send a GET request.
   * @param path - API path to fetch.
   */
  get<T>(path: string) {
    return this.request<T>(path);
  }

  /**
   * Send a POST request with a JSON body.
   * @param path - API path to post to.
   * @param body - Request payload (will be JSON-serialized).
   */
  post<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  /**
   * Send a PATCH request with a JSON body.
   * @param path - API path to patch.
   * @param body - Partial update payload (will be JSON-serialized).
   */
  patch<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  /**
   * Send a DELETE request.
   * @param path - API path to delete.
   */
  delete<T>(path: string) {
    return this.request<T>(path, { method: "DELETE" });
  }

  /**
   * Upload a file via multipart form data.
   * @param path - API path to upload to.
   * @param file - The File object to upload.
   * @param fieldName - The form field name (default "file").
   * @returns An ApiResponse with either data or error populated.
   */
  async upload<T>(
    path: string,
    file: File,
    fieldName = "file"
  ): Promise<ApiResponse<T>> {
    const formData = new FormData();
    formData.append(fieldName, file);

    const headers: Record<string, string> = {};
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers,
      body: formData,
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
}

/** Pre-configured API client instance pointing to the backend. */
export const api = new ApiClient(API_BASE_URL);
