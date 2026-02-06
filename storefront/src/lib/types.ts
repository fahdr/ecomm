/**
 * Shared TypeScript types for the storefront app.
 *
 * **For Developers:**
 *   These types mirror the backend's public API response schemas.
 *   Keep them in sync with ``backend/app/schemas/public.py``.
 */

/**
 * Public store data returned by ``GET /api/v1/public/stores/{slug}``.
 */
export interface Store {
  /** Unique store identifier (UUID). */
  id: string;
  /** Display name of the store. */
  name: string;
  /** URL-friendly unique slug. */
  slug: string;
  /** Product niche or category. */
  niche: string;
  /** Optional longer description. */
  description: string | null;
  /** ISO 8601 timestamp of store creation. */
  created_at: string;
}
