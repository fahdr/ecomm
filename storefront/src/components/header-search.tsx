/**
 * Header search component for the storefront with theme-aware styling.
 *
 * Renders a search icon button in the header that, when clicked,
 * navigates to the search page. On larger screens it can also show
 * a compact inline search input. All elements use theme-driven CSS
 * classes for consistent branding.
 *
 * **For Developers:**
 *   This is a client component that uses Next.js router for navigation.
 *   The compact form submits to ``/search?q=...`` via form action.
 *   The input uses ``border-theme`` for borders, ``bg-theme-surface``
 *   for background, and ``text-theme-muted`` for placeholder text via
 *   the ``placeholder:text-theme-muted`` class. The search icon button
 *   uses ``text-theme-muted`` for its default color.
 *
 * **For QA Engineers:**
 *   - Clicking the search icon navigates to ``/search``.
 *   - Pressing Enter in the inline input navigates with the query.
 *   - The inline input is hidden on mobile, shown on desktop.
 *   - Input border uses ``border-theme``.
 *   - Input background uses ``bg-theme-surface``.
 *   - Placeholder text uses ``text-theme-muted``.
 *   - Focus ring uses the theme primary color.
 *
 * **For Project Managers:**
 *   Search is a critical discovery tool. The compact header search
 *   provides quick access without leaving the current page, while
 *   the full search page handles detailed results.
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
 * Features a togglable inline input (visible on desktop) and a
 * search icon button. All elements use theme-aware CSS classes.
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
   * Trims the query string and navigates to ``/search`` with the
   * query as a URL parameter. Collapses the input and resets state.
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
            className="w-40 rounded-md border border-theme bg-theme-surface px-3 py-1 text-sm placeholder:text-theme-muted focus:outline-none focus:ring-1 focus:ring-theme-primary transition-all"
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
        className="relative inline-flex items-center text-theme-muted hover:opacity-75 transition-opacity"
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
