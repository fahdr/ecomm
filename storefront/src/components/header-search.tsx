/**
 * Header search component for the storefront.
 *
 * Renders a search icon button in the header that, when clicked,
 * navigates to the search page. On larger screens it can also show
 * a compact inline search input.
 *
 * **For Developers:**
 *   This is a client component that uses Next.js router for navigation.
 *   The compact form submits to ``/search?q=...`` via form action.
 *
 * **For QA Engineers:**
 *   - Clicking the search icon navigates to ``/search``.
 *   - Pressing Enter in the inline input navigates with the query.
 *   - The inline input is hidden on mobile, shown on desktop.
 *
 * **For End Users:**
 *   Click the search icon or type in the search bar to find products.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

/**
 * Compact search control for the store header.
 *
 * @returns A search icon button and optional inline search input.
 */
export function HeaderSearch() {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const [query, setQuery] = useState("");

  /**
   * Handle form submission to navigate to the search page.
   *
   * @param e - The form submit event.
   */
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    } else {
      router.push("/search");
    }
    setExpanded(false);
    setQuery("");
  }

  return (
    <div className="flex items-center">
      {/* Expanded inline search (desktop) */}
      {expanded && (
        <form onSubmit={handleSubmit} className="hidden sm:flex mr-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search..."
            autoFocus
            onBlur={() => {
              /* Collapse after a short delay to allow form submission. */
              setTimeout(() => {
                setExpanded(false);
                setQuery("");
              }, 200);
            }}
            className="w-40 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-zinc-400 transition-all"
          />
        </form>
      )}

      {/* Search icon button */}
      <button
        onClick={() => {
          if (expanded) {
            /* If already expanded, navigate to search page. */
            router.push("/search");
            setExpanded(false);
          } else {
            setExpanded(true);
          }
        }}
        className="relative inline-flex items-center text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
        title="Search products"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="h-5 w-5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
          />
        </svg>
      </button>
    </div>
  );
}
