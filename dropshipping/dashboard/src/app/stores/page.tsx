/**
 * Store list page.
 *
 * Displays all of the authenticated user's stores in a card grid layout.
 * Each card shows the store name, niche, status badge, and links to the
 * store settings page. Includes a "Create Store" button.
 *
 * **For End Users:**
 *   This is your stores overview. Click any store card to manage it,
 *   or click "Create Store" to set up a new one.
 *
 * **For QA Engineers:**
 *   - Deleted stores are excluded by the API (soft-delete filter).
 *   - An empty state message is shown when no stores exist.
 *   - Renders inside the unified dashboard shell (sidebar + top bar).
 *   - Cards have hover lift animation and staggered entrance.
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
import { EmptyState } from "@/components/empty-state";
import { FadeIn } from "@/components/motion-wrappers";
import { AuthenticatedLayout } from "@/components/authenticated-layout";
import { Store, Plus } from "lucide-react";

/** Store data returned by the API. */
interface StoreData {
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
  const [stores, setStores] = useState<StoreData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user) return;

    async function fetchStores() {
      const result = await api.get<StoreData[]>("/api/v1/stores");
      if (result.data) setStores(result.data);
      setLoading(false);
    }

    fetchStores();
  }, [user, authLoading]);

  return (
    <AuthenticatedLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="font-heading text-2xl font-bold">Stores</h1>
          <Link href="/stores/new">
            <Button>
              <Plus className="size-4" />
              Create Store
            </Button>
          </Link>
        </div>

        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="h-36 rounded-xl border bg-muted/30 animate-pulse"
              />
            ))}
          </div>
        ) : stores.length === 0 ? (
          <EmptyState
            icon={<Store className="size-6" />}
            title="No stores yet"
            description="Create your first store to get started with dropshipping."
            action={
              <Link href="/stores/new">
                <Button>
                  <Plus className="size-4" />
                  Create your first store
                </Button>
              </Link>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {stores.map((store, index) => (
              <FadeIn key={store.id} delay={index * 0.05}>
                <Link href={`/stores/${store.id}`}>
                  <Card className="cursor-pointer transition-all hover:shadow-md hover:-translate-y-0.5">
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <CardTitle className="font-heading text-base">
                          {store.name}
                        </CardTitle>
                        <Badge
                          variant={
                            store.status === "active" ? "success" : "secondary"
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
              </FadeIn>
            ))}
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
