/**
 * Products page — browse and analyze tracked products across all competitors.
 *
 * Displays a filterable, sortable grid of competitor products with
 * price change indicators, status badges, and expandable price history.
 * Users can filter by status, sort by various fields, and click into
 * individual products for detailed price history charts.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/products/` with pagination, status filter,
 *     and sort_by query parameters.
 *   - Product detail uses `GET /api/v1/products/{id}` for full price history.
 *   - Uses Shell wrapper for authenticated layout.
 *   - Motion animations: PageTransition for the page, StaggerChildren for
 *     the product grid, FadeIn for header and filters.
 *   - Loading state shows skeleton product cards.
 *
 * **For Project Managers:**
 *   - The product feed gives users a unified view across all competitors.
 *   - Price change indicators help users spot opportunities quickly.
 *   - Filtering and sorting reduce time to find relevant products.
 *
 * **For QA Engineers:**
 *   - Verify filter buttons toggle correctly and update the product list.
 *   - Test sorting by each field (last seen, first seen, price, title).
 *   - Check pagination controls with large datasets.
 *   - Verify the price history dialog shows correct data and timeline.
 *   - Test with zero products — should show empty state.
 *   - Verify price change badges show correct direction (up/down).
 *
 * **For End Users:**
 *   - Browse all products across your monitored competitor stores.
 *   - Use filters to show only active or removed products.
 *   - Sort by price to find the cheapest products, or by date to see recent changes.
 *   - Click "View History" on a product to see its full price timeline.
 */

"use client";

import * as React from "react";
import {
  Package,
  TrendingDown,
  TrendingUp,
  Minus,
  ArrowUpDown,
  Filter,
  RefreshCw,
  ExternalLink,
  History,
  X,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  FadeIn,
  StaggerChildren,
  PageTransition,
  AnimatedCounter,
} from "@/components/motion";
import { api } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────

/** A single price history entry for a product. */
interface PriceHistoryEntry {
  /** ISO date string of the price observation. */
  date: string;
  /** The product price at that date. */
  price: number;
}

/** Shape of a single product from the API. */
interface CompetitorProduct {
  /** Unique identifier (UUID). */
  id: string;
  /** Parent competitor UUID. */
  competitor_id: string;
  /** Product title. */
  title: string;
  /** Direct URL to the product page. */
  url: string;
  /** Product image URL, or null. */
  image_url: string | null;
  /** Current product price, or null. */
  price: number | null;
  /** Currency code (e.g. USD). */
  currency: string;
  /** When the product was first discovered. */
  first_seen: string;
  /** When the product was last seen in a scan. */
  last_seen: string;
  /** Full price history array. */
  price_history: PriceHistoryEntry[];
  /** Product availability status (active, removed). */
  status: string;
  /** Name of the parent competitor store. */
  competitor_name: string | null;
  /** Record creation timestamp. */
  created_at: string;
  /** Last update timestamp. */
  updated_at: string;
}

/** Paginated product list response from the API. */
interface ProductListResponse {
  items: CompetitorProduct[];
  total: number;
  page: number;
  per_page: number;
}

// ── Constants ────────────────────────────────────────────────────────

/** Available sort options for the product list. */
const SORT_OPTIONS = [
  { value: "last_seen", label: "Last Seen" },
  { value: "first_seen", label: "First Seen" },
  { value: "price", label: "Price (Low to High)" },
  { value: "title", label: "Title (A-Z)" },
];

/** Available status filter options. */
const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "active", label: "Active" },
  { value: "removed", label: "Removed" },
];

// ── Component ────────────────────────────────────────────────────────

/**
 * Products page component.
 *
 * Displays a filterable, sortable product grid with price change
 * indicators, status badges, and price history dialog.
 *
 * @returns The products page wrapped in the Shell layout.
 */
export default function ProductsPage() {
  const [products, setProducts] = React.useState<CompetitorProduct[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Filtering and sorting
  const [statusFilter, setStatusFilter] = React.useState("");
  const [sortBy, setSortBy] = React.useState("last_seen");

  // Price history dialog
  const [selectedProduct, setSelectedProduct] =
    React.useState<CompetitorProduct | null>(null);
  const [detailLoading, setDetailLoading] = React.useState(false);

  const perPage = 20;

  /**
   * Fetch the paginated product list from the API with current filters.
   * Updates products, total, loading, and error state.
   */
  const fetchProducts = React.useCallback(async () => {
    setLoading(true);
    setError(null);

    let url = `/api/v1/products/?page=${page}&per_page=${perPage}&sort_by=${sortBy}`;
    if (statusFilter) {
      url += `&status=${statusFilter}`;
    }

    const { data, error: apiError } = await api.get<ProductListResponse>(url);
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setProducts(data.items);
      setTotal(data.total);
    }
    setLoading(false);
  }, [page, sortBy, statusFilter]);

  React.useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  /**
   * Open the price history dialog for a product.
   * Fetches the full product detail with price history from the API.
   *
   * @param product - The product to show history for.
   */
  async function handleViewHistory(product: CompetitorProduct) {
    setSelectedProduct(product);
    setDetailLoading(true);

    const { data } = await api.get<CompetitorProduct>(
      `/api/v1/products/${product.id}`
    );
    if (data) {
      setSelectedProduct(data);
    }
    setDetailLoading(false);
  }

  /**
   * Compute the price change between the first and last price history entries.
   *
   * @param product - The product to analyze.
   * @returns An object with direction ('up', 'down', 'flat'), amount, and percentage.
   */
  function getPriceChange(product: CompetitorProduct): {
    direction: "up" | "down" | "flat";
    amount: number;
    percent: number;
  } {
    const history = product.price_history;
    if (!history || history.length < 2) {
      return { direction: "flat", amount: 0, percent: 0 };
    }
    const oldest = history[0].price;
    const newest = history[history.length - 1].price;
    const amount = newest - oldest;
    const percent =
      oldest > 0 ? Math.abs(Math.round((amount / oldest) * 100)) : 0;

    if (amount < 0) return { direction: "down", amount: Math.abs(amount), percent };
    if (amount > 0) return { direction: "up", amount, percent };
    return { direction: "flat", amount: 0, percent: 0 };
  }

  /**
   * Format a currency value.
   *
   * @param price - The numeric price.
   * @param currency - The currency code (e.g. USD).
   * @returns Formatted price string.
   */
  function formatPrice(price: number | null, currency: string): string {
    if (price === null) return "N/A";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency || "USD",
    }).format(price);
  }

  /**
   * Format a date string into a short relative or absolute format.
   *
   * @param dateStr - ISO date string.
   * @returns Formatted date string.
   */
  function formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours < 1) return "Just now";
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  }

  /**
   * Reset filters and sorting to defaults.
   */
  function resetFilters() {
    setStatusFilter("");
    setSortBy("last_seen");
    setPage(1);
  }

  const totalPages = Math.ceil(total / perPage);
  const hasFilters = statusFilter !== "" || sortBy !== "last_seen";

  return (
    <Shell>
      <PageTransition className="p-6 space-y-6">
        {/* ── Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight flex items-center gap-2">
                <Package className="size-6 text-primary" />
                Products
              </h2>
              <p className="text-muted-foreground mt-1">
                Browse and analyze tracked products across all competitor stores.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchProducts}
              disabled={loading}
            >
              <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </FadeIn>

        {/* ── Summary Cards ── */}
        <FadeIn delay={0.1}>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Products
                </CardTitle>
                <Package className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={total}
                  className="text-3xl font-bold font-heading"
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Price Drops
                </CardTitle>
                <TrendingDown className="size-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={
                    products.filter(
                      (p) => getPriceChange(p).direction === "down"
                    ).length
                  }
                  className="text-3xl font-bold font-heading text-emerald-600"
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Price Increases
                </CardTitle>
                <TrendingUp className="size-4 text-red-500" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={
                    products.filter(
                      (p) => getPriceChange(p).direction === "up"
                    ).length
                  }
                  className="text-3xl font-bold font-heading text-red-600"
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Active Products
                </CardTitle>
                <Filter className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={
                    products.filter((p) => p.status === "active").length
                  }
                  className="text-3xl font-bold font-heading"
                />
              </CardContent>
            </Card>
          </div>
        </FadeIn>

        {/* ── Filters & Sort ── */}
        <FadeIn delay={0.15}>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5">
              <Filter className="size-4 text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground">
                Status:
              </span>
              {STATUS_FILTERS.map((filter) => (
                <Button
                  key={filter.value}
                  variant={statusFilter === filter.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => {
                    setStatusFilter(filter.value);
                    setPage(1);
                  }}
                >
                  {filter.label}
                </Button>
              ))}
            </div>

            <div className="h-6 w-px bg-border" />

            <div className="flex items-center gap-1.5">
              <ArrowUpDown className="size-4 text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground">
                Sort:
              </span>
              <select
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setPage(1);
                }}
                className="h-8 rounded-md border border-input bg-background px-2 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {hasFilters && (
              <Button variant="ghost" size="sm" onClick={resetFilters}>
                <X className="size-3.5" />
                Clear Filters
              </Button>
            )}
          </div>
        </FadeIn>

        {/* ── Product Grid ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-6 space-y-3">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                  <div className="flex justify-between mt-4">
                    <Skeleton className="h-6 w-20" />
                    <Skeleton className="h-6 w-16 rounded-full" />
                  </div>
                  <Skeleton className="h-8 w-full mt-2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">
                  Failed to load products: {error}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={fetchProducts}
                >
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : products.length === 0 ? (
          <FadeIn>
            <Card className="border-dashed">
              <CardContent className="pt-6 pb-6 text-center">
                <Package className="size-12 text-muted-foreground mx-auto mb-4 opacity-40" />
                <h3 className="font-heading text-lg font-semibold">
                  No products found
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-md mx-auto">
                  {hasFilters
                    ? "No products match your current filters. Try clearing filters or adjusting your search."
                    : "Products will appear here after your competitor stores are scanned. Add competitors and trigger a scan to get started."}
                </p>
                {hasFilters && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4"
                    onClick={resetFilters}
                  >
                    Clear Filters
                  </Button>
                )}
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <>
            <StaggerChildren
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
              staggerDelay={0.05}
            >
              {products.map((product) => {
                const change = getPriceChange(product);
                return (
                  <Card
                    key={product.id}
                    className="group hover:shadow-md transition-shadow duration-200"
                  >
                    <CardContent className="pt-6">
                      {/* Title and competitor */}
                      <div className="mb-3">
                        <h3 className="font-medium text-sm leading-snug line-clamp-2">
                          {product.title}
                        </h3>
                        {product.competitor_name && (
                          <p className="text-xs text-muted-foreground mt-1">
                            from{" "}
                            <span className="font-medium">
                              {product.competitor_name}
                            </span>
                          </p>
                        )}
                      </div>

                      {/* Price and change indicator */}
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-lg font-bold font-heading">
                          {formatPrice(product.price, product.currency)}
                        </span>
                        <div className="flex items-center gap-2">
                          {change.direction === "down" && (
                            <Badge
                              variant="success"
                              className="flex items-center gap-1"
                            >
                              <TrendingDown className="size-3" />
                              {change.percent}%
                            </Badge>
                          )}
                          {change.direction === "up" && (
                            <Badge
                              variant="destructive"
                              className="flex items-center gap-1"
                            >
                              <TrendingUp className="size-3" />
                              {change.percent}%
                            </Badge>
                          )}
                          {change.direction === "flat" && (
                            <Badge
                              variant="secondary"
                              className="flex items-center gap-1"
                            >
                              <Minus className="size-3" />
                              Stable
                            </Badge>
                          )}
                          <Badge variant={product.status === "active" ? "success" : "secondary"}>
                            {product.status}
                          </Badge>
                        </div>
                      </div>

                      {/* Mini price timeline bar */}
                      {product.price_history && product.price_history.length > 1 && (
                        <div className="mb-3">
                          <div className="flex items-end gap-0.5 h-8">
                            {product.price_history.slice(-10).map((entry, i) => {
                              const allPrices = product.price_history
                                .slice(-10)
                                .map((e) => e.price);
                              const max = Math.max(...allPrices);
                              const min = Math.min(...allPrices);
                              const range = max - min || 1;
                              const height =
                                20 + ((entry.price - min) / range) * 80;

                              return (
                                <div
                                  key={i}
                                  className={`flex-1 rounded-sm transition-all ${
                                    i === product.price_history.slice(-10).length - 1
                                      ? "bg-primary"
                                      : "bg-primary/30"
                                  }`}
                                  style={{ height: `${height}%` }}
                                  title={`${formatPrice(entry.price, product.currency)} - ${new Date(entry.date).toLocaleDateString()}`}
                                />
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Timestamps */}
                      <div className="flex items-center justify-between text-xs text-muted-foreground mb-3">
                        <span>Seen: {formatDate(product.last_seen)}</span>
                        <span>Found: {formatDate(product.first_seen)}</span>
                      </div>

                      {/* Actions */}
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() => handleViewHistory(product)}
                        >
                          <History className="size-3.5" />
                          View History
                        </Button>
                        <Button variant="ghost" size="icon" className="size-8" asChild>
                          <a
                            href={product.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title="Open product page"
                          >
                            <ExternalLink className="size-3.5" />
                          </a>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </StaggerChildren>

            {/* Pagination */}
            {totalPages > 1 && (
              <FadeIn>
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Showing {(page - 1) * perPage + 1}–
                    {Math.min(page * perPage, total)} of {total} products
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </FadeIn>
            )}
          </>
        )}

        {/* ── Price History Dialog ── */}
        <Dialog
          open={!!selectedProduct}
          onOpenChange={(open) => !open && setSelectedProduct(null)}
        >
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="text-base">
                Price History
              </DialogTitle>
              <DialogDescription className="line-clamp-2">
                {selectedProduct?.title}
                {selectedProduct?.competitor_name && (
                  <span className="text-muted-foreground">
                    {" "}from {selectedProduct.competitor_name}
                  </span>
                )}
              </DialogDescription>
            </DialogHeader>
            {detailLoading ? (
              <div className="space-y-3 py-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex justify-between">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                ))}
              </div>
            ) : selectedProduct?.price_history &&
              selectedProduct.price_history.length > 0 ? (
              <div className="py-2">
                {/* Current price highlight */}
                <div className="flex items-center justify-between py-3 px-4 rounded-lg bg-secondary/50 mb-4">
                  <span className="text-sm font-medium text-muted-foreground">
                    Current Price
                  </span>
                  <span className="text-xl font-bold font-heading">
                    {formatPrice(
                      selectedProduct.price,
                      selectedProduct.currency
                    )}
                  </span>
                </div>

                {/* Price timeline */}
                <div className="space-y-1 max-h-64 overflow-y-auto">
                  {[...selectedProduct.price_history]
                    .reverse()
                    .map((entry, i, arr) => {
                      const prevEntry = arr[i + 1];
                      const priceDiff = prevEntry
                        ? entry.price - prevEntry.price
                        : 0;

                      return (
                        <div
                          key={i}
                          className="flex items-center justify-between py-2 px-3 rounded-md hover:bg-secondary/30 transition-colors"
                        >
                          <span className="text-sm text-muted-foreground">
                            {new Date(entry.date).toLocaleDateString("en-US", {
                              year: "numeric",
                              month: "short",
                              day: "numeric",
                            })}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-medium">
                              {formatPrice(entry.price, selectedProduct.currency)}
                            </span>
                            {priceDiff !== 0 && (
                              <span
                                className={`text-xs font-medium ${
                                  priceDiff < 0
                                    ? "text-emerald-600"
                                    : "text-red-600"
                                }`}
                              >
                                {priceDiff < 0 ? "" : "+"}
                                {formatPrice(
                                  priceDiff,
                                  selectedProduct.currency
                                )}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                </div>

                {/* Summary stats */}
                {selectedProduct.price_history.length >= 2 && (
                  <div className="mt-4 pt-4 border-t grid grid-cols-3 gap-4 text-center">
                    <div>
                      <p className="text-xs text-muted-foreground">Lowest</p>
                      <p className="font-mono text-sm font-bold text-emerald-600">
                        {formatPrice(
                          Math.min(
                            ...selectedProduct.price_history.map((e) => e.price)
                          ),
                          selectedProduct.currency
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Highest</p>
                      <p className="font-mono text-sm font-bold text-red-600">
                        {formatPrice(
                          Math.max(
                            ...selectedProduct.price_history.map((e) => e.price)
                          ),
                          selectedProduct.currency
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">
                        Data Points
                      </p>
                      <p className="font-mono text-sm font-bold">
                        {selectedProduct.price_history.length}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-8 text-center">
                <History className="size-10 text-muted-foreground mx-auto mb-3 opacity-40" />
                <p className="text-sm text-muted-foreground">
                  No price history available yet. Price history builds up as scans discover
                  price changes over time.
                </p>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
