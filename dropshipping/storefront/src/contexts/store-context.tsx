/**
 * Store context provider for the storefront.
 *
 * Makes the resolved store data available to all client components
 * in the component tree. The store is resolved server-side in the
 * root layout and passed down via this provider.
 *
 * **For Developers:**
 *   Use the ``useStore()`` hook in client components to access store data.
 *   The store may be null if no slug was resolved or the store wasn't found.
 *
 * **For QA Engineers:**
 *   - ``useStore()`` returns null when no store is resolved.
 *   - The provider must wrap any component that calls ``useStore()``.
 */

"use client";

import { createContext, useContext } from "react";
import type { Store } from "@/lib/types";

/**
 * React context holding the current store data.
 * Defaults to null when no store is resolved.
 */
const StoreContext = createContext<Store | null>(null);

/**
 * Provider component that passes store data to the component tree.
 *
 * @param props - Provider props.
 * @param props.store - The resolved store data, or null.
 * @param props.children - Child components that can consume the context.
 * @returns A context provider wrapping the children.
 */
export function StoreProvider({
  store,
  children,
}: {
  store: Store | null;
  children: React.ReactNode;
}) {
  return (
    <StoreContext.Provider value={store}>{children}</StoreContext.Provider>
  );
}

/**
 * Hook to access the current store data from context.
 *
 * @returns The resolved Store object, or null if no store is available.
 *
 * @example
 * ```tsx
 * const store = useStore();
 * if (!store) return <p>No store found</p>;
 * return <h1>{store.name}</h1>;
 * ```
 */
export function useStore(): Store | null {
  return useContext(StoreContext);
}
