/**
 * Customer list page for the dashboard.
 *
 * Displays all customers registered on a store with pagination and search.
 * Store owners can click through to individual customer details.
 *
 * **For Developers:**
 *   Client component. Customers are fetched from the authenticated
 *   customers API. Search filters by email, first name, or last name.
 *
 * **For QA Engineers:**
 *   - Customers are listed with email, name, join date, order count, total spent.
 *   - Search input filters results in real-time (debounced).
 *   - Empty state shows "No customers yet" message.
 *   - Each row links to the customer detail page.
 *   - Pagination controls appear when there are multiple pages.
 *
 * **For End Users (Store Owners):**
 *   View all customers who have registered on your store. Search by
 *   name or email to find specific customers.
 */

"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
} from "@/components/ui/card";

/** Customer data returned by the API. */
interface CustomerSummary {
  id: string;
  store_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  is_active: boolean;
  created_at: string;
}

/** Paginated customer list response. */
interface PaginatedCustomers {
  items: CustomerSummary[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

/**
 * Customer list page component.
 *
 * @param props - Page props containing the store ID parameter.
 * @returns The customer list page with search and pagination.
 */
export default function CustomersListPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: storeId } = use(params);
  const { user, loading: authLoading } = useAuth();
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const perPage = 20;

  useEffect(() => {
    if (authLoading || !user) return;

    async function fetchCustomers() {
      setLoading(true);
      let url = `/api/v1/stores/${storeId}/customers/?page=${page}&per_page=${perPage}`;
      if (search.trim()) {
        url += `&search=${encodeURIComponent(search.trim())}`;
      }
      const result = await api.get<PaginatedCustomers>(url);
      if (result.data) {
        setCustomers(result.data.items);
        setTotal(result.data.total);
        setPages(result.data.pages);
      }
      setLoading(false);
    }

    const timer = setTimeout(fetchCustomers, search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [storeId, page, search, user, authLoading]);

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading customers...</p>
      </div>
    );
  }

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
          <h1 className="text-lg font-semibold">Customers</h1>
        </div>
      </header>

      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Search */}
        <div className="flex items-center gap-4">
          <Input
            placeholder="Search by email or name..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="max-w-sm"
          />
          <span className="text-sm text-muted-foreground">
            {total} customer{total !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Customer List */}
        {customers.length === 0 ? (
          <Card>
            <CardContent className="pt-6 text-center">
              <p className="text-muted-foreground">
                {search ? "No customers match your search." : "No customers yet."}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {customers.map((cust) => (
              <Link
                key={cust.id}
                href={`/stores/${storeId}/customers/${cust.id}`}
              >
                <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <p className="font-medium">
                          {cust.first_name || cust.last_name
                            ? `${cust.first_name || ""} ${cust.last_name || ""}`.trim()
                            : cust.email}
                        </p>
                        {(cust.first_name || cust.last_name) && (
                          <p className="text-sm text-muted-foreground">
                            {cust.email}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground">
                          Joined {new Date(cust.created_at).toLocaleDateString()}
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
    </div>
  );
}
