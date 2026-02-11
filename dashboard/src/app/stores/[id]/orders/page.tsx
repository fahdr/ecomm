/**
 * Orders list page for the dashboard.
 *
 * Displays all orders for a store with pagination and status filtering.
 * Store owners can click through to individual order details.
 *
 * **For Developers:**
 *   This is a client component. Orders are fetched from the authenticated
 *   orders API. Pagination and status filtering are controlled via state.
 *   Uses `useStore()` from the store context for the store ID.
 *
 * **For QA Engineers:**
 *   - Orders are listed in reverse chronological order.
 *   - Status filter dropdown filters by order status.
 *   - Empty state shows "No orders yet" message.
 *   - Each row links to the order detail page.
 *   - Pagination controls appear when there are multiple pages.
 *
 * **For End Users:**
 *   View all orders placed on your store. Filter by status to find
 *   specific orders. Click any order to see its details.
 *
 * **For Project Managers:**
 *   Part of the core order management flow in the dashboard.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download } from "lucide-react";
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

/** Order data returned by the API. */
interface Order {
  id: string;
  store_id: string;
  customer_email: string;
  status: string;
  total: string;
  created_at: string;
  items: Array<{
    id: string;
    product_title: string;
    quantity: number;
    unit_price: string;
  }>;
}

/** Paginated order list response. */
interface PaginatedOrders {
  items: Order[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

/**
 * Map order status to badge variant for visual differentiation.
 * @param status - The order status string.
 * @returns A badge variant suitable for the shadcn Badge component.
 */
function statusBadge(status: string) {
  const map: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    pending: "outline",
    paid: "default",
    shipped: "secondary",
    delivered: "default",
    cancelled: "destructive",
  };
  return map[status] || "outline";
}

/**
 * Orders list page component.
 *
 * Renders a filterable, paginated list of order cards.
 *
 * @returns The orders list page wrapped in a PageTransition.
 */
export default function OrdersListPage() {
  const { store } = useStore();
  const storeId = store?.id ?? "";
  const { user, loading: authLoading } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const perPage = 20;

  useEffect(() => {
    if (authLoading || !user || !storeId) return;

    /**
     * Fetch orders with current status filter and pagination.
     */
    async function fetchOrders() {
      setLoading(true);
      let url = `/api/v1/stores/${storeId}/orders?page=${page}&per_page=${perPage}`;
      if (statusFilter !== "all") {
        url += `&status=${statusFilter}`;
      }
      const result = await api.get<PaginatedOrders>(url);
      if (result.data) {
        setOrders(result.data.items);
        setTotal(result.data.total);
        setPages(result.data.pages);
      }
      setLoading(false);
    }

    fetchOrders();
  }, [storeId, page, statusFilter, user, authLoading]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-muted-foreground">Loading orders...</p>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-heading font-bold">Orders</h1>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => {
              const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
              window.open(`${API_BASE}/api/v1/stores/${storeId}/exports/orders`, "_blank");
            }}
          >
            <Download className="h-3.5 w-3.5" />
            Export CSV
          </Button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4">
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="paid">Paid</SelectItem>
              <SelectItem value="shipped">Shipped</SelectItem>
              <SelectItem value="delivered">Delivered</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-sm text-muted-foreground">
            {total} order{total !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Orders List */}
        {orders.length === 0 ? (
          <Card>
            <CardContent className="pt-6 text-center">
              <p className="text-muted-foreground">No orders yet.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {orders.map((order) => (
              <Link key={order.id} href={`/stores/${storeId}/orders/${order.id}`}>
                <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-sm">
                            {order.id.slice(0, 8)}...
                          </span>
                          <Badge variant={statusBadge(order.status)}>
                            {order.status}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {order.customer_email}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(order.created_at).toLocaleString()} &middot;{" "}
                          {order.items.length} item{order.items.length !== 1 ? "s" : ""}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-semibold">
                          ${Number(order.total).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-center gap-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {page} of {pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(pages, p + 1))}
              disabled={page >= pages}
            >
              Next
            </Button>
          </div>
        )}
      </main>
    </PageTransition>
  );
}
