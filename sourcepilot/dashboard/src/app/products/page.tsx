/**
 * Product Search page — search supplier catalogs and import products.
 *
 * Users can search across AliExpress, CJ Dropshipping, and Spocket
 * catalogs, preview product details, and import directly to their store.
 *
 * **For Developers:**
 *   - Search calls `GET /api/v1/products/search?q=...&source=...&page=1&page_size=20`.
 *   - Product preview calls `POST /api/v1/products/preview` with the product URL.
 *   - Import-to-store triggers `POST /api/v1/imports` with the selected product.
 *   - Results rendered as a responsive card grid with image placeholders.
 *   - Debounced search not implemented — user must press Enter or click Search.
 *
 * **For Project Managers:**
 *   - Discovery workflow: search -> preview -> import. Three clicks to a new product.
 *   - Source selector lets users switch between supplier catalogs.
 *   - Product cards show key info at a glance (image, title, price, rating).
 *
 * **For QA Engineers:**
 *   - Test search with empty query — should show validation hint.
 *   - Test each source option returns different results.
 *   - Verify product preview modal displays full details.
 *   - Test "Import to Store" button in preview modal.
 *   - Verify loading state during search and preview.
 *   - Test with no results — should show empty state.
 *   - Check image fallback when product has no image.
 *
 * **For End Users:**
 *   - Type a product name or keyword and click Search to browse supplier catalogs.
 *   - Switch the source dropdown to search different suppliers.
 *   - Click a product card to see full details before importing.
 *   - Use "Import to Store" to add the product to your store.
 */

"use client";

import * as React from "react";
import {
  Search,
  Package,
  Star,
  Download,
  Loader2,
  X,
  ImageOff,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { FadeIn, StaggerChildren, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";

/** Shape of a product in search results. */
interface SearchProduct {
  id: string;
  title: string;
  price: number;
  currency: string;
  image_url?: string;
  rating?: number;
  review_count?: number;
  source: string;
  source_url: string;
  seller?: string;
  shipping_cost?: number;
  orders_count?: number;
}

/** Paginated search results response. */
interface SearchResponse {
  items: SearchProduct[];
  total: number;
  page: number;
  page_size: number;
}

/** Detailed product preview from the API. */
interface ProductPreview {
  title: string;
  description: string;
  price: number;
  currency: string;
  images: string[];
  variants: Array<{
    name: string;
    options: string[];
  }>;
  shipping_info: string;
  seller: string;
  rating: number;
  review_count: number;
  source: string;
  source_url: string;
}

/** Available supplier sources for the search dropdown. */
const SOURCES = [
  { value: "aliexpress", label: "AliExpress" },
  { value: "cj", label: "CJ Dropshipping" },
  { value: "spocket", label: "Spocket" },
];

/**
 * Product Search page component.
 *
 * @returns The product search page wrapped in the Shell layout.
 */
export default function ProductsPage() {
  const [query, setQuery] = React.useState("");
  const [source, setSource] = React.useState("aliexpress");
  const [results, setResults] = React.useState<SearchProduct[]>([]);
  const [totalResults, setTotalResults] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [searching, setSearching] = React.useState(false);
  const [hasSearched, setHasSearched] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  /** Preview modal state. */
  const [previewOpen, setPreviewOpen] = React.useState(false);
  const [previewData, setPreviewData] = React.useState<ProductPreview | null>(
    null
  );
  const [previewLoading, setPreviewLoading] = React.useState(false);
  const [importing, setImporting] = React.useState(false);

  /** Number of results per search page. */
  const pageSize = 20;
  const totalPages = Math.ceil(totalResults / pageSize);

  /**
   * Execute a product search against the API.
   *
   * @param searchPage - The page number to fetch (defaults to current page).
   */
  async function handleSearch(searchPage: number = page) {
    if (!query.trim()) return;

    setSearching(true);
    setError(null);
    setHasSearched(true);

    const { data, error: apiError } = await api.get<SearchResponse>(
      `/api/v1/products/search?q=${encodeURIComponent(query.trim())}&source=${source}&page=${searchPage}&page_size=${pageSize}`
    );

    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setResults(data.items);
      setTotalResults(data.total);
      setPage(data.page);
    }
    setSearching(false);
  }

  /**
   * Handle Enter key press in the search input.
   *
   * @param e - The keyboard event.
   */
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      setPage(1);
      handleSearch(1);
    }
  }

  /**
   * Open the product preview modal and fetch detailed product data.
   *
   * @param product - The search result product to preview.
   */
  async function handlePreview(product: SearchProduct) {
    setPreviewOpen(true);
    setPreviewLoading(true);
    setPreviewData(null);

    const { data } = await api.post<ProductPreview>("/api/v1/products/preview", {
      source_url: product.source_url,
      source: product.source,
    });

    if (data) {
      setPreviewData(data);
    }
    setPreviewLoading(false);
  }

  /**
   * Import the currently previewed product to the user's store.
   * Creates an import job via the imports API.
   */
  async function handleImport() {
    if (!previewData) return;

    setImporting(true);
    await api.post("/api/v1/imports", {
      source: previewData.source,
      source_url: previewData.source_url,
      store_id: "default",
      markup_percent: 30,
      tags: [],
    });
    setImporting(false);
    setPreviewOpen(false);
  }

  /**
   * Navigate to a different page of search results.
   *
   * @param newPage - The target page number.
   */
  function goToPage(newPage: number) {
    setPage(newPage);
    handleSearch(newPage);
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Header ── */}
        <FadeIn direction="down">
          <div>
            <h2 className="font-heading text-2xl font-bold tracking-tight">
              Product Search
            </h2>
            <p className="text-muted-foreground mt-1">
              Search supplier catalogs to find products for your store
            </p>
          </div>
        </FadeIn>

        {/* ── Search Bar ── */}
        <FadeIn delay={0.1}>
          <div className="flex gap-3">
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring min-w-[150px]"
            >
              {SOURCES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                placeholder="Search for products (e.g., wireless earbuds, phone case)..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                className="pl-9"
              />
            </div>
            <Button
              onClick={() => {
                setPage(1);
                handleSearch(1);
              }}
              disabled={searching || !query.trim()}
            >
              {searching ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Search className="size-4" />
              )}
              Search
            </Button>
          </div>
        </FadeIn>

        {/* ── Error State ── */}
        {error && (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">
                  Search failed: {error}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => handleSearch()}
                >
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* ── Loading State ── */}
        {searching && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Card key={i}>
                <Skeleton className="h-48 rounded-t-xl rounded-b-none" />
                <CardContent className="pt-4 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-6 w-20" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* ── Empty State (before search) ── */}
        {!searching && !hasSearched && (
          <FadeIn delay={0.2}>
            <Card>
              <CardContent className="pt-6 text-center py-16">
                <Search className="size-12 text-muted-foreground/40 mx-auto mb-4" />
                <h3 className="font-heading text-lg font-semibold mb-2">
                  Discover products from top suppliers
                </h3>
                <p className="text-muted-foreground text-sm max-w-md mx-auto">
                  Enter a keyword above to search across AliExpress, CJ
                  Dropshipping, and Spocket catalogs.
                </p>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* ── No Results State ── */}
        {!searching && hasSearched && results.length === 0 && !error && (
          <FadeIn>
            <Card>
              <CardContent className="pt-6 text-center py-12">
                <Package className="size-12 text-muted-foreground/40 mx-auto mb-4" />
                <h3 className="font-heading text-lg font-semibold mb-2">
                  No products found
                </h3>
                <p className="text-muted-foreground text-sm">
                  Try a different search term or switch to another supplier.
                </p>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* ── Search Results Grid ── */}
        {!searching && results.length > 0 && (
          <>
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {totalResults} products found
              </p>
            </div>
            <StaggerChildren
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
              staggerDelay={0.05}
            >
              {results.map((product) => (
                <Card
                  key={product.id}
                  className="overflow-hidden cursor-pointer hover:border-primary/40 transition-colors group"
                  onClick={() => handlePreview(product)}
                >
                  {/* Product Image */}
                  <div className="relative h-48 bg-secondary/30 overflow-hidden">
                    {product.image_url ? (
                      <img
                        src={product.image_url}
                        alt={product.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full">
                        <ImageOff className="size-10 text-muted-foreground/30" />
                      </div>
                    )}
                    <Badge className="absolute top-2 right-2 capitalize" variant="secondary">
                      {product.source}
                    </Badge>
                  </div>

                  <CardContent className="pt-4 space-y-2">
                    {/* Title */}
                    <p className="font-medium text-sm line-clamp-2 leading-snug">
                      {product.title}
                    </p>

                    {/* Rating */}
                    {product.rating !== undefined && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Star className="size-3 fill-amber-400 text-amber-400" />
                        <span>{product.rating.toFixed(1)}</span>
                        {product.review_count !== undefined && (
                          <span>({product.review_count.toLocaleString()})</span>
                        )}
                        {product.orders_count !== undefined && (
                          <span className="ml-1">
                            &middot; {product.orders_count.toLocaleString()} sold
                          </span>
                        )}
                      </div>
                    )}

                    {/* Price */}
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-bold font-heading text-primary">
                        {product.currency === "USD" ? "$" : product.currency}
                        {product.price.toFixed(2)}
                      </span>
                      <Button size="sm" variant="outline" className="text-xs">
                        <Download className="size-3" />
                        Import
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </StaggerChildren>

            {/* ── Pagination ── */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Page {page} of {totalPages}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => goToPage(page - 1)}
                    disabled={page <= 1}
                  >
                    <ChevronLeft className="size-4" />
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => goToPage(page + 1)}
                    disabled={page >= totalPages}
                  >
                    Next
                    <ChevronRight className="size-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}

        {/* ── Product Preview Dialog ── */}
        <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
          <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-heading">Product Preview</DialogTitle>
              <DialogDescription>
                Review product details before importing to your store.
              </DialogDescription>
            </DialogHeader>

            {previewLoading ? (
              <div className="space-y-4 py-4">
                <Skeleton className="h-64 w-full rounded-lg" />
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : previewData ? (
              <div className="space-y-4 py-2">
                {/* Product Image Gallery */}
                {previewData.images.length > 0 && (
                  <div className="relative h-64 bg-secondary/20 rounded-lg overflow-hidden">
                    <img
                      src={previewData.images[0]}
                      alt={previewData.title}
                      className="w-full h-full object-contain"
                    />
                  </div>
                )}

                {/* Title & Price */}
                <div>
                  <h3 className="font-heading font-bold text-lg leading-tight">
                    {previewData.title}
                  </h3>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-2xl font-bold text-primary">
                      ${previewData.price.toFixed(2)}
                    </span>
                    {previewData.rating > 0 && (
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Star className="size-4 fill-amber-400 text-amber-400" />
                        {previewData.rating.toFixed(1)}
                        <span>({previewData.review_count} reviews)</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Seller & Shipping */}
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>Seller: {previewData.seller}</span>
                  <span>&middot;</span>
                  <span>{previewData.shipping_info}</span>
                </div>

                {/* Description */}
                <div>
                  <h4 className="font-medium text-sm mb-1">Description</h4>
                  <p className="text-sm text-muted-foreground line-clamp-6">
                    {previewData.description}
                  </p>
                </div>

                {/* Variants */}
                {previewData.variants.length > 0 && (
                  <div>
                    <h4 className="font-medium text-sm mb-2">Variants</h4>
                    <div className="space-y-2">
                      {previewData.variants.map((variant, idx) => (
                        <div key={idx}>
                          <span className="text-xs font-medium text-muted-foreground">
                            {variant.name}:
                          </span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {variant.options.map((opt, oidx) => (
                              <Badge key={oidx} variant="outline" className="text-xs">
                                {opt}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-sm text-muted-foreground">
                  Failed to load product preview.
                </p>
              </div>
            )}

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">
                  <X className="size-4" />
                  Close
                </Button>
              </DialogClose>
              <Button
                onClick={handleImport}
                disabled={importing || !previewData}
              >
                {importing ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Download className="size-4" />
                )}
                {importing ? "Importing..." : "Import to Store"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
