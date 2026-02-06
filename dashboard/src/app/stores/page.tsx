/**
 * Store list page.
 *
 * Displays all of the authenticated user's stores in a card grid layout.
 * Each card shows the store name, niche, status badge, and links to the
 * store settings page. Includes a "Create Store" button in the header.
 *
 * **For End Users:**
 *   This is your stores overview. Click any store card to manage it,
 *   or click "Create Store" to set up a new one.
 *
 * **For QA Engineers:**
 *   - Deleted stores are excluded by the API (soft-delete filter).
 *   - An empty state message is shown when no stores exist.
 *   - The page redirects to `/login` if unauthenticated (via middleware).
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

/** Store data returned by the API. */
interface Store {
  id: string;
  name: string;
  slug: string;
  niche: string;
  description: string | null;
  status: "active" | "paused" | "deleted";
  created_at: string;
}

export default function StoresPage() {
  const { user, loading: authLoading } = useAuth();
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user) return;

    async function fetchStores() {
      const result = await api.get<Store[]>("/api/v1/stores");
      if (result.data) {
        setStores(result.data);
      }
      setLoading(false);
    }

    fetchStores();
  }, [user, authLoading]);

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading stores...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-lg font-semibold hover:underline">
            Dashboard
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">Stores</h1>
        </div>
        <Link href="/stores/new">
          <Button>Create Store</Button>
        </Link>
      </header>

      <main className="p-6">
        {stores.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-12 text-center">
            <h2 className="text-xl font-semibold">No stores yet</h2>
            <p className="text-muted-foreground">
              Create your first store to get started with dropshipping.
            </p>
            <Link href="/stores/new">
              <Button>Create your first store</Button>
            </Link>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {stores.map((store) => (
              <Link key={store.id} href={`/stores/${store.id}`}>
                <Card className="cursor-pointer transition-shadow hover:shadow-md">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-base">{store.name}</CardTitle>
                      <Badge
                        variant={
                          store.status === "active" ? "default" : "secondary"
                        }
                      >
                        {store.status}
                      </Badge>
                    </div>
                    <CardDescription>{store.niche}</CardDescription>
                  </CardHeader>
                  {store.description && (
                    <CardContent>
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {store.description}
                      </p>
                    </CardContent>
                  )}
                </Card>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
