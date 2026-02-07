/**
 * Customer detail page for the dashboard.
 *
 * Shows a customer's profile, order statistics, and order history.
 * Accessible to the store owner via the dashboard.
 *
 * **For Developers:**
 *   Client component fetching customer detail and orders from the
 *   authenticated customers API. Uses ``customerDetailResponse``
 *   which includes order_count and total_spent.
 *
 * **For QA Engineers:**
 *   - Shows customer email, name, phone, join date.
 *   - Stats: total orders and total spent.
 *   - Order history is paginated and clickable.
 *   - Non-existent customer shows "Customer not found".
 *
 * **For End Users (Store Owners):**
 *   View detailed information about a specific customer including
 *   their order history and total spending.
 */

"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** Customer detail with stats. */
interface CustomerDetail {
  id: string;
  store_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  is_active: boolean;
  created_at: string;
  order_count: number;
  total_spent: number;
}

/** Order summary for the customer's order list. */
interface Order {
  id: string;
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

/** Map order status to badge variant. */
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
 * Customer detail page component.
 *
 * @param props - Page props containing storeId and customerId parameters.
 * @returns The customer detail view with profile and order history.
 */
export default function CustomerDetailPage({
  params,
}: {
  params: Promise<{ id: string; customerId: string }>;
}) {
  const { id: storeId, customerId } = use(params);
  const { user, loading: authLoading } = useAuth();

  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [loading, setLoading] = useState(true);

  const [orders, setOrders] = useState<Order[]>([]);
  const [orderPage, setOrderPage] = useState(1);
  const [orderPages, setOrderPages] = useState(1);
  const [ordersLoading, setOrdersLoading] = useState(true);

  // Fetch customer detail
  useEffect(() => {
    if (authLoading || !user) return;

    async function fetchCustomer() {
      const result = await api.get<CustomerDetail>(
        `/api/v1/stores/${storeId}/customers/${customerId}`
      );
      if (result.error) {
        setNotFound(true);
      } else if (result.data) {
        setCustomer(result.data);
      }
      setLoading(false);
    }

    fetchCustomer();
  }, [storeId, customerId, user, authLoading]);

  // Fetch customer orders
  useEffect(() => {
    if (authLoading || !user) return;

    async function fetchOrders() {
      setOrdersLoading(true);
      const result = await api.get<PaginatedOrders>(
        `/api/v1/stores/${storeId}/customers/${customerId}/orders?page=${orderPage}&per_page=10`
      );
      if (result.data) {
        setOrders(result.data.items);
        setOrderPages(result.data.pages);
      }
      setOrdersLoading(false);
    }

    fetchOrders();
  }, [storeId, customerId, orderPage, user, authLoading]);

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading customer...</p>
      </div>
    );
  }

  if (notFound || !customer) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <h2 className="text-xl font-semibold">Customer not found</h2>
        <Link href={`/stores/${storeId}/customers`}>
          <Button variant="outline">Back to customers</Button>
        </Link>
      </div>
    );
  }

  const displayName =
    customer.first_name || customer.last_name
      ? `${customer.first_name || ""} ${customer.last_name || ""}`.trim()
      : customer.email;

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/stores" className="text-lg font-semibold hover:underline">
            Stores
          </Link>
          <span className="text-muted-foreground">/</span>
          <Link
            href={`/stores/${storeId}`}
            className="text-lg font-semibold hover:underline"
          >
            Settings
          </Link>
          <span className="text-muted-foreground">/</span>
          <Link
            href={`/stores/${storeId}/customers`}
            className="text-lg font-semibold hover:underline"
          >
            Customers
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">{displayName}</h1>
        </div>
      </header>

      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Customer Profile */}
        <Card>
          <CardHeader>
            <CardTitle>{displayName}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Email:</span>
                <p className="font-medium">{customer.email}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Phone:</span>
                <p className="font-medium">{customer.phone || "—"}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Joined:</span>
                <p className="font-medium">
                  {new Date(customer.created_at).toLocaleDateString()}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Status:</span>
                <p>
                  <Badge variant={customer.is_active ? "default" : "secondary"}>
                    {customer.is_active ? "Active" : "Inactive"}
                  </Badge>
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4">
          <Card>
            <CardContent className="pt-6 text-center">
              <p className="text-3xl font-bold">{customer.order_count}</p>
              <p className="text-sm text-muted-foreground mt-1">Total Orders</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <p className="text-3xl font-bold">
                ${Number(customer.total_spent).toFixed(2)}
              </p>
              <p className="text-sm text-muted-foreground mt-1">Total Spent</p>
            </CardContent>
          </Card>
        </div>

        {/* Order History */}
        <Card>
          <CardHeader>
            <CardTitle>Order History</CardTitle>
          </CardHeader>
          <CardContent>
            {ordersLoading ? (
              <p className="text-muted-foreground text-center py-4">
                Loading orders...
              </p>
            ) : orders.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">
                No orders yet.
              </p>
            ) : (
              <div className="space-y-3">
                {orders.map((order) => (
                  <Link
                    key={order.id}
                    href={`/stores/${storeId}/orders/${order.id}`}
                  >
                    <div className="flex items-center justify-between rounded-lg border p-3 hover:bg-muted/50 transition-colors cursor-pointer">
                      <div className="space-y-1">
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-sm">
                            {order.id.slice(0, 8)}...
                          </span>
                          <Badge variant={statusBadge(order.status)}>
                            {order.status}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {new Date(order.created_at).toLocaleString()} &middot;{" "}
                          {order.items.length} item{order.items.length !== 1 ? "s" : ""}
                        </p>
                      </div>
                      <p className="text-lg font-semibold">
                        ${Number(order.total).toFixed(2)}
                      </p>
                    </div>
                  </Link>
                ))}

                {orderPages > 1 && (
                  <div className="flex items-center justify-center gap-4 pt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setOrderPage((p) => Math.max(1, p - 1))}
                      disabled={orderPage <= 1}
                    >
                      Previous
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      Page {orderPage} of {orderPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setOrderPage((p) => Math.min(orderPages, p + 1))}
                      disabled={orderPage >= orderPages}
                    >
                      Next
                    </Button>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
