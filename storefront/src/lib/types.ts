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

/**
 * Customer profile returned by the storefront auth endpoints.
 */
export interface Customer {
  /** Unique customer identifier (UUID). */
  id: string;
  /** Store this customer belongs to (UUID). */
  store_id: string;
  /** Customer email address. */
  email: string;
  /** Optional first name. */
  first_name: string | null;
  /** Optional last name. */
  last_name: string | null;
  /** Optional phone number. */
  phone: string | null;
  /** Whether the customer account is active. */
  is_active: boolean;
  /** ISO 8601 timestamp of account creation. */
  created_at: string;
}

/**
 * Token response from customer login/register endpoints.
 */
export interface CustomerTokenResponse {
  /** JWT access token for authenticated requests. */
  access_token: string;
  /** JWT refresh token for session renewal. */
  refresh_token: string;
  /** Token type (always "bearer"). */
  token_type: string;
}

/**
 * Order item within an order.
 */
export interface OrderItem {
  /** Unique order item identifier (UUID). */
  id: string;
  /** Product title at time of purchase. */
  product_title: string;
  /** Variant name, if any. */
  variant_name: string | null;
  /** Quantity purchased. */
  quantity: number;
  /** Unit price at time of purchase. */
  unit_price: string;
}

/**
 * Order data returned by the customer account API.
 */
export interface Order {
  /** Unique order identifier (UUID). */
  id: string;
  /** Store this order belongs to (UUID). */
  store_id: string;
  /** Customer email used for the order. */
  customer_email: string;
  /** Customer ID if placed by a logged-in customer. */
  customer_id: string | null;
  /** Order status (pending, paid, shipped, delivered, cancelled). */
  status: string;
  /** Total order amount. */
  total: string;
  /** ISO 8601 timestamp of order creation. */
  created_at: string;
  /** Line items in the order. */
  items: OrderItem[];
}

/**
 * Paginated order list response.
 */
export interface PaginatedOrders {
  /** Orders on this page. */
  items: Order[];
  /** Total number of orders. */
  total: number;
  /** Current page number (1-based). */
  page: number;
  /** Items per page. */
  per_page: number;
  /** Total number of pages. */
  pages: number;
}

/**
 * Wishlist item returned by the customer account API.
 */
export interface WishlistItem {
  /** Unique wishlist item identifier (UUID). */
  id: string;
  /** Customer who saved this item (UUID). */
  customer_id: string;
  /** Product that was saved (UUID). */
  product_id: string;
  /** ISO 8601 timestamp when the item was saved. */
  created_at: string;
  /** Nested product data. */
  product: Product;
}

/**
 * Paginated wishlist response.
 */
export interface PaginatedWishlist {
  /** Wishlist items on this page. */
  items: WishlistItem[];
  /** Total number of wishlist items. */
  total: number;
  /** Current page number (1-based). */
  page: number;
  /** Items per page. */
  per_page: number;
  /** Total number of pages. */
  pages: number;
}
