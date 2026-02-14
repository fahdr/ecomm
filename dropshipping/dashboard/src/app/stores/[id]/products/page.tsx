/**
 * Product list page for a store.
 *
 * Displays products in a card grid with search, status filter, and pagination.
 * Provides actions to create new products and navigate to edit existing ones.
 *
 * **For End Users:**
 *   View all your products, search by name, filter by status, and manage
 *   individual products from this page.
 *
 * **For QA Engineers:**
 *   - Products are fetched from ``/api/v1/stores/{store_id}/products``.
 *   - Archived products are excluded by default unless explicitly filtered.
 *   - Search is case-insensitive and filters by title.
 *   - Pagination controls appear when there are more items than ``per_page``.
 *
 * **For Developers:**
 *   - Uses `useStore()` from the store context to obtain the store ID.
 *   - Wrapped in `<PageTransition>` for consistent page entrance animations.
 *   - The old breadcrumb header has been removed; navigation is handled
 *     by the shell sidebar.
 *
 * **For Project Managers:**
 *   Core product management listing. Part of the store dashboard sub-pages.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Product data returned by the API. */
interface Product {
  id: string;
  title: string;
  slug: string;
  price: string;
  status: "draft" | "active" | "archived";
  images: string[] | null;
  created_at: string;
}

/** Paginated product list response. */
interface PaginatedProducts {
  items: Product[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

/**
 * Product list page component.
 *
 * Renders a searchable, filterable grid of product cards with pagination.
 *
 * @returns The product list page wrapped in a PageTransition.
 */
export default function ProductListPage() {
  const { store } = useStore();
  const storeId = store?.id ?? "";
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState<PaginatedProducts | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const perPage = 20;

  useEffect(() => {
    if (authLoading || !user || !storeId) return;

    /**
     * Fetch products with current search, status filter, and pagination.
     */
    async function fetchProducts() {
      setLoading(true);
      let url = `/api/v1/stores/${storeId}/products?page=${page}&per_page=${perPage}`;
      if (search) url += `&search=${encodeURIComponent(search)}`;
      if (statusFilter !== "all") url += `&status=${statusFilter}`;

      const result = await api.get<PaginatedProducts>(url);
      if (result.data) {
        setData(result.data);
      }
      setLoading(false);
    }

    fetchProducts();
  }, [storeId, user, authLoading, page, search, statusFilter]);

  /**
   * Handle search input with reset to page 1.
   * @param value - The new search string.
   */
  function handleSearch(value: string) {
    setSearch(value);
    setPage(1);
  }

  /**
   * Handle status filter change with reset to page 1.
   * @param value - The new status filter value.
   */
  function handleStatusFilter(value: string) {
    setStatusFilter(value);
    setPage(1);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-muted-foreground">Loading products...</p>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-heading font-bold">Products</h1>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => {
                const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                window.open(`${API_BASE}/api/v1/stores/${storeId}/exports/products`, "_blank");
              }}
            >
              Export CSV
            </Button>
            <Link href={`/stores/${storeId}/products/new`}>
              <Button size="sm">Add Product</Button>
            </Link>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <Input
            placeholder="Search products..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="max-w-xs"
          />
          <Select value={statusFilter} onValueChange={handleStatusFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-sm text-muted-foreground">
            {data?.total ?? 0} product{data?.total !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Product Grid */}
        {data && data.items.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-12 text-center">
            <h2 className="text-xl font-semibold">No products found</h2>
            <p className="text-muted-foreground">
              {search || statusFilter !== "all"
                ? "Try adjusting your filters."
                : "Add your first product to start selling."}
            </p>
            {!search && statusFilter === "all" && (
              <Link href={`/stores/${storeId}/products/new`}>
                <Button>Add your first product</Button>
              </Link>
            )}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {data?.items.map((product) => (
              <Link
                key={product.id}
                href={`/stores/${storeId}/products/${product.id}`}
              >
                <Card className="cursor-pointer transition-shadow hover:shadow-md h-full">
                  {/* Image placeholder */}
                  <div className="aspect-square bg-muted flex items-center justify-center rounded-t-lg overflow-hidden">
                    {product.images && product.images.length > 0 ? (
                      <img
                        src={product.images[0]}
                        alt={product.title}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="text-4xl text-muted-foreground/30">
                        &#128247;
                      </div>
                    )}
                  </div>
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-sm font-medium line-clamp-2">
                        {product.title}
                      </CardTitle>
                      <Badge
                        variant={
                          product.status === "active"
                            ? "default"
                            : product.status === "draft"
                              ? "secondary"
                              : "outline"
                        }
                        className="shrink-0"
                      >
                        {product.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <p className="text-lg font-semibold">
                      ${Number(product.price).toFixed(2)}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="flex items-center justify-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {data.page} of {data.pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.pages}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </main>
    </PageTransition>
  );
}
