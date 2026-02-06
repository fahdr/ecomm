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

/**
 * Public variant data returned in product responses.
 */
export interface ProductVariant {
  /** Unique variant identifier (UUID). */
  id: string;
  /** Display name of the variant (e.g. "Large", "Blue"). */
  name: string;
  /** Optional stock-keeping unit identifier. */
  sku: string | null;
  /** Optional price override (uses product base price if null). */
  price: string | null;
  /** Number of units in stock. */
  inventory_count: number;
}

/**
 * Public product data returned by the public API.
 * Excludes sensitive fields like ``cost`` and ``store_id``.
 */
export interface Product {
  /** Unique product identifier (UUID). */
  id: string;
  /** Display title of the product. */
  title: string;
  /** URL-friendly slug (unique within the store). */
  slug: string;
  /** Optional product description. */
  description: string | null;
  /** Selling price as a string decimal. */
  price: string;
  /** Optional compare-at (original) price. */
  compare_at_price: string | null;
  /** List of image URL strings. */
  images: string[] | null;
  /** Optional SEO title. */
  seo_title: string | null;
  /** Optional SEO meta description. */
  seo_description: string | null;
  /** ISO 8601 timestamp of product creation. */
  created_at: string;
  /** Product variants (sizes, colors, etc.). */
  variants: ProductVariant[];
}

/**
 * Paginated product list response from the public API.
 */
export interface PaginatedProducts {
  /** Products on this page. */
  items: Product[];
  /** Total number of matching products. */
  total: number;
  /** Current page number (1-based). */
  page: number;
  /** Items per page. */
  per_page: number;
  /** Total number of pages. */
  pages: number;
}
