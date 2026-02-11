/**
 * Top bar component for the unified dashboard shell.
 *
 * Displays dynamic breadcrumbs based on the current route, a store
 * switcher dropdown (when stores exist), and the user email with logout.
 *
 * **For Developers:**
 *   Uses ``usePathname()`` + store context to build breadcrumbs.
 *   Each breadcrumb segment is clickable except the last.
 *
 * **For QA:**
 *   - Breadcrumbs update on every navigation
 *   - Store switcher shows all user stores
 *   - Current store highlighted in switcher dropdown
 *   - Logout button clears auth state and redirects to /login
 *
 * **For End Users:**
 *   The top bar shows where you are in the dashboard and lets you
 *   quickly switch between stores.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, LogOut, Store as StoreIcon } from "lucide-react";
import { useStore, type StoreData } from "@/contexts/store-context";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/** A single breadcrumb segment. */
interface BreadcrumbItem {
  label: string;
  href: string;
}

/**
 * Builds breadcrumb items from the current pathname and store context.
 *
 * @param pathname - The current URL pathname.
 * @param store - The current store data (null on platform pages).
 * @returns Array of breadcrumb items.
 */
function buildBreadcrumbs(
  pathname: string,
  store: StoreData | null
): BreadcrumbItem[] {
  const crumbs: BreadcrumbItem[] = [{ label: "Home", href: "/" }];
  const segments = pathname.split("/").filter(Boolean);

  if (segments.length === 0) return crumbs;

  // /stores
  if (segments[0] === "stores") {
    crumbs.push({ label: "Stores", href: "/stores" });

    // /stores/new
    if (segments[1] === "new") {
      crumbs.push({ label: "Create", href: "/stores/new" });
      return crumbs;
    }

    // /stores/[id]
    if (segments[1] && store) {
      crumbs.push({
        label: store.name,
        href: `/stores/${store.id}`,
      });

      // /stores/[id]/products, /stores/[id]/orders, etc.
      if (segments[2]) {
        const sectionLabel = segments[2]
          .split("-")
          .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(" ");
        crumbs.push({
          label: sectionLabel,
          href: `/stores/${store.id}/${segments[2]}`,
        });

        // /stores/[id]/products/[productId] or /stores/[id]/orders/[orderId]
        if (segments[3] && segments[3] !== "new") {
          crumbs.push({
            label: "Detail",
            href: pathname,
          });
        } else if (segments[3] === "new") {
          crumbs.push({
            label: "New",
            href: pathname,
          });
        }
      }
    }
    return crumbs;
  }

  // Top-level pages: /billing, /notifications, /pricing
  const topLevel: Record<string, string> = {
    billing: "Billing",
    notifications: "Notifications",
    pricing: "Pricing",
  };
  if (topLevel[segments[0]]) {
    crumbs.push({
      label: topLevel[segments[0]],
      href: `/${segments[0]}`,
    });
  }

  return crumbs;
}

/**
 * Top bar with breadcrumbs, store switcher, and user menu.
 *
 * @returns The top bar element.
 */
export function TopBar() {
  const pathname = usePathname();
  const { store } = useStore();
  const { user, logout } = useAuth();
  const [stores, setStores] = useState<StoreData[]>([]);
  const [switcherOpen, setSwitcherOpen] = useState(false);

  const crumbs = buildBreadcrumbs(pathname, store);

  // Fetch all user stores for the switcher
  useEffect(() => {
    async function fetchStores() {
      const result = await api.get<StoreData[]>("/api/v1/stores");
      if (result.data) setStores(result.data);
    }
    fetchStores();
  }, []);

  return (
    <header className="flex h-12 items-center justify-between border-b bg-background/80 backdrop-blur-sm px-4 shrink-0">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1 text-sm min-w-0">
        {crumbs.map((crumb, i) => {
          const isLast = i === crumbs.length - 1;
          return (
            <span key={crumb.href} className="flex items-center gap-1 min-w-0">
              {i > 0 && (
                <ChevronRight className="size-3 text-muted-foreground/50 shrink-0" />
              )}
              {isLast ? (
                <span className="font-medium truncate">{crumb.label}</span>
              ) : (
                <Link
                  href={crumb.href}
                  className="text-muted-foreground hover:text-foreground transition-colors truncate"
                >
                  {crumb.label}
                </Link>
              )}
            </span>
          );
        })}
      </nav>

      {/* Right side: Store switcher + User */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Store switcher */}
        {stores.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setSwitcherOpen(!switcherOpen)}
              className="flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-muted/50 transition-colors"
            >
              <StoreIcon className="size-3" />
              <span className="max-w-[120px] truncate">
                {store?.name || "Select store"}
              </span>
            </button>
            {switcherOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setSwitcherOpen(false)}
                />
                <div className="absolute right-0 top-full mt-1 z-50 w-56 rounded-lg border bg-popover shadow-lg py-1">
                  {stores.map((s) => (
                    <Link
                      key={s.id}
                      href={`/stores/${s.id}`}
                      onClick={() => setSwitcherOpen(false)}
                      className={cn(
                        "flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted/50 transition-colors",
                        store?.id === s.id && "bg-muted/30 font-medium"
                      )}
                    >
                      <StoreIcon className="size-3.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="truncate">{s.name}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {s.niche}
                        </p>
                      </div>
                      {store?.id === s.id && (
                        <div className="size-1.5 rounded-full bg-primary shrink-0" />
                      )}
                    </Link>
                  ))}
                  <div className="my-1 h-px bg-border" />
                  <Link
                    href="/stores/new"
                    onClick={() => setSwitcherOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-primary hover:bg-muted/50 transition-colors"
                  >
                    + Create Store
                  </Link>
                </div>
              </>
            )}
          </div>
        )}

        {/* User email + logout */}
        {user && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground hidden sm:inline">
              {user.email}
            </span>
            <button
              onClick={logout}
              className="flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:text-destructive hover:bg-muted/50 transition-colors"
              title="Log out"
            >
              <LogOut className="size-3.5" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
