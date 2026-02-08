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

// ---------------------------------------------------------------------------
// Categories (Feature 9)
// ---------------------------------------------------------------------------

/**
 * Public category data returned by ``GET /api/v1/public/stores/{slug}/categories``.
 *
 * **For Developers:**
 *   Categories represent the hierarchical product groupings for a store.
 *   ``parent_id`` is null for top-level categories.
 */
export interface Category {
  /** Unique category identifier (UUID). */
  id: string;
  /** Display name of the category. */
  name: string;
  /** URL-friendly slug, unique within the store. */
  slug: string;
  /** Optional description text. */
  description: string | null;
  /** Optional category image URL. */
  image_url: string | null;
  /** Parent category UUID (null for top-level). */
  parent_id: string | null;
  /** Number of active products in this category. */
  product_count: number;
}

/**
 * Paginated products within a category from the public API.
 */
export interface PaginatedCategoryProducts {
  /** Products on this page. */
  items: Product[];
  /** Total number of products in this category. */
  total: number;
  /** Current page number (1-based). */
  page: number;
  /** Items per page. */
  per_page: number;
  /** Total number of pages. */
  pages: number;
  /** The category these products belong to. */
  category: Category;
}

// ---------------------------------------------------------------------------
// Reviews (Feature 12)
// ---------------------------------------------------------------------------

/**
 * Public review data returned by the reviews endpoint.
 *
 * **For Developers:**
 *   Only approved reviews are visible on the public storefront.
 *   ``verified_purchase`` indicates the reviewer bought the product.
 */
export interface Review {
  /** Unique review identifier (UUID). */
  id: string;
  /** Reviewer display name. */
  customer_name: string | null;
  /** Star rating (1-5). */
  rating: number;
  /** Optional review headline. */
  title: string | null;
  /** Review body text. */
  body: string | null;
  /** Whether the reviewer made a verified purchase. */
  verified_purchase: boolean;
  /** ISO 8601 timestamp of submission. */
  created_at: string;
}

/**
 * Paginated review list with aggregate rating.
 */
export interface PaginatedReviews {
  /** Reviews on this page. */
  items: Review[];
  /** Total number of approved reviews. */
  total: number;
  /** Current page number (1-based). */
  page: number;
  /** Items per page. */
  per_page: number;
  /** Total number of pages. */
  pages: number;
  /** Average star rating across all approved reviews. */
  average_rating: string | null;
}

/**
 * Payload for submitting a new review.
 */
export interface SubmitReviewPayload {
  /** Reviewer email (used for purchase verification). */
  customer_email: string;
  /** Reviewer display name. */
  customer_name: string;
  /** Star rating (1-5). */
  rating: number;
  /** Optional review headline. */
  title: string;
  /** Review body text. */
  body: string;
}

// ---------------------------------------------------------------------------
// Search (Feature 17)
// ---------------------------------------------------------------------------

/**
 * A single search result product.
 *
 * **For Developers:**
 *   Search results may include a relevance_score used for ranking.
 */
export interface SearchProduct {
  /** Product UUID. */
  id: string;
  /** Product title. */
  title: string;
  /** Product URL slug. */
  slug: string;
  /** Selling price as a string decimal. */
  price: string;
  /** Optional compare-at price. */
  compare_at_price: string | null;
  /** Product image URLs. */
  images: string[];
  /** Truncated product description. */
  description: string | null;
  /** Search relevance score (higher is better). */
  relevance_score: number | null;
}

/**
 * Paginated search results from the public search API.
 */
export interface PaginatedSearchResults {
  /** Matching products on this page. */
  items: SearchProduct[];
  /** Total number of matching products. */
  total: number;
  /** Current page number (1-based). */
  page: number;
  /** Items per page. */
  per_page: number;
  /** Total number of pages. */
  pages: number;
  /** The search query that was executed. */
  query: string | null;
}

// ---------------------------------------------------------------------------
// Gift Cards (Feature 20)
// ---------------------------------------------------------------------------

/**
 * Response from the public gift card validation endpoint.
 *
 * **For Developers:**
 *   Used on the cart page to let customers check gift card balance
 *   before applying it at checkout.
 */
export interface GiftCardValidation {
  /** Whether the gift card code is valid and usable. */
  valid: boolean;
  /** Remaining balance as a decimal string (null if invalid). */
  balance: string | null;
  /** Human-readable validation message. */
  message: string;
}

// ---------------------------------------------------------------------------
// Upsells / Cross-Sells (Feature 18)
// ---------------------------------------------------------------------------

/**
 * Public upsell recommendation for a product.
 *
 * **For Developers:**
 *   Upsells are displayed on the product detail page as
 *   "You might also like" recommendations.
 */
export interface UpsellRecommendation {
  /** Recommended product UUID. */
  target_product_id: string;
  /** Product title. */
  target_product_title: string;
  /** Product slug for linking. */
  target_product_slug: string;
  /** Product price as a decimal string. */
  target_product_price: string;
  /** Primary product image URL (may be null). */
  target_product_image: string | null;
  /** Type of recommendation: upsell, cross_sell, or bundle. */
  upsell_type: "upsell" | "cross_sell" | "bundle";
  /** Display title for the recommendation section. */
  title: string | null;
  /** Optional description. */
  description: string | null;
  /** Optional discount percentage on the target product. */
  discount_percent: string | null;
}
