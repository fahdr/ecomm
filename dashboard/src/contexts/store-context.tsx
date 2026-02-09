/**
 * Store context for sharing the current store data within store-scoped pages.
 *
 * Provides the active store's ID, name, and slug to all child components
 * within a store's route group, avoiding redundant API calls across pages.
 *
 * **For Developers:**
 *   - Used by the stores/[id]/layout.tsx to provide store data to sub-pages
 *   - Access via useStore() hook in any client component under /stores/[id]/
 *   - The sidebar reads store name and ID from this context
 *
 * **For QA:**
 *   - Store data should be loaded once per store route and shared across pages
 *   - Navigating between sub-pages should not refetch store data
 */

"use client";

import { createContext, useContext, useMemo } from "react";

/** Shape of the store data available in context. */
export interface StoreData {
  /** Unique store identifier (UUID). */
  id: string;
  /** Display name of the store. */
  name: string;
  /** URL-friendly slug for the store. */
  slug: string;
  /** Store niche category. */
  niche: string;
  /** Current store status. */
  status: "active" | "paused" | "deleted";
}

interface StoreContextValue {
  /** The current store data, or null if not yet loaded. */
  store: StoreData | null;
  /** Refresh the store data (call after updates). */
  refreshStore: () => void;
}

const StoreContext = createContext<StoreContextValue | null>(null);

/**
 * Provider component that wraps store-scoped pages with store data.
 *
 * @param store - The current store data.
 * @param refreshStore - Callback to refetch store data.
 * @param children - Child components that can access store via useStore().
 */
export function StoreProvider({
  store,
  refreshStore,
  children,
}: {
  store: StoreData | null;
  refreshStore: () => void;
  children: React.ReactNode;
}) {
  const value = useMemo(
    () => ({ store, refreshStore }),
    [store, refreshStore]
  );

  return (
    <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
  );
}

/**
 * Hook to access the current store context.
 *
 * Must be used within a StoreProvider (i.e., under /stores/[id]/ routes).
 *
 * @returns The store context value with store data and refresh function.
 * @throws Error if used outside of StoreProvider.
 */
export function useStore(): StoreContextValue {
  const context = useContext(StoreContext);
  if (!context) {
    throw new Error("useStore must be used within a StoreProvider");
  }
  return context;
}
