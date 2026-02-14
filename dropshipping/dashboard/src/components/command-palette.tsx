/**
 * Command Palette -- a Cmd+K / Ctrl+K triggered modal for quick navigation
 * and actions across the dashboard.
 *
 * **For Developers:**
 *   This is a **client component** that renders a dialog with a search input.
 *   It provides two sections: Pages (navigation) and Actions (create/manage).
 *   Results filter as the user types using a simple substring match.
 *   Keyboard navigation: Up/Down arrows + Enter to select.
 *
 * **For QA Engineers:**
 *   - Cmd+K (Mac) or Ctrl+K (Windows/Linux) toggles the palette.
 *   - Escape closes the palette.
 *   - Typing filters results in real-time.
 *   - Enter navigates to the selected result.
 *   - Arrow keys highlight items; Enter activates.
 *
 * **For End Users:**
 *   Press Cmd+K to quickly navigate to any page or create new items.
 *
 * @module components/command-palette
 */

"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/contexts/store-context";

/** A command palette entry. */
interface CommandItem {
  label: string;
  section: "Pages" | "Actions";
  href?: string;
  action?: () => void;
  keywords?: string;
}

/**
 * Build the list of available commands based on the current store context.
 *
 * @param storeId - Current store ID (if any).
 * @returns Array of command items.
 */
function buildCommands(storeId?: string): CommandItem[] {
  const items: CommandItem[] = [
    { label: "Home", section: "Pages", href: "/", keywords: "dashboard home overview" },
    { label: "All Stores", section: "Pages", href: "/stores", keywords: "stores list" },
    { label: "Create Store", section: "Actions", href: "/stores/new", keywords: "new store create" },
    { label: "Billing", section: "Pages", href: "/billing", keywords: "billing subscription plan" },
    { label: "Pricing", section: "Pages", href: "/pricing", keywords: "pricing plans" },
    { label: "Notifications", section: "Pages", href: "/notifications", keywords: "notifications alerts" },
  ];

  if (storeId) {
    items.push(
      { label: "Store Overview", section: "Pages", href: `/stores/${storeId}`, keywords: "overview settings" },
      { label: "Products", section: "Pages", href: `/stores/${storeId}/products`, keywords: "products catalog" },
      { label: "Orders", section: "Pages", href: `/stores/${storeId}/orders`, keywords: "orders sales" },
      { label: "Customers", section: "Pages", href: `/stores/${storeId}/customers`, keywords: "customers users" },
      { label: "Analytics", section: "Pages", href: `/stores/${storeId}/analytics`, keywords: "analytics stats revenue" },
      { label: "Categories", section: "Pages", href: `/stores/${storeId}/categories`, keywords: "categories collections" },
      { label: "Discounts", section: "Pages", href: `/stores/${storeId}/discounts`, keywords: "discounts coupons promotions" },
      { label: "Reviews", section: "Pages", href: `/stores/${storeId}/reviews`, keywords: "reviews ratings" },
      { label: "Themes", section: "Pages", href: `/stores/${storeId}/themes`, keywords: "themes design customization" },
      { label: "Gift Cards", section: "Pages", href: `/stores/${storeId}/gift-cards`, keywords: "gift cards" },
      { label: "Suppliers", section: "Pages", href: `/stores/${storeId}/suppliers`, keywords: "suppliers vendors" },
      { label: "Upsells", section: "Pages", href: `/stores/${storeId}/upsells`, keywords: "upsells cross-sells" },
      { label: "Tax Settings", section: "Pages", href: `/stores/${storeId}/tax`, keywords: "tax rates" },
      { label: "Webhooks", section: "Pages", href: `/stores/${storeId}/webhooks`, keywords: "webhooks integrations" },
      { label: "Team", section: "Pages", href: `/stores/${storeId}/team`, keywords: "team members" },
      { label: "Refunds", section: "Pages", href: `/stores/${storeId}/refunds`, keywords: "refunds returns" },
      { label: "Add Product", section: "Actions", href: `/stores/${storeId}/products/new`, keywords: "new product create add" },
    );
  }

  return items;
}

/**
 * Render the command palette modal.
 *
 * @returns The command palette component (renders nothing when closed).
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const storeCtx = useStore();
  const storeId = storeCtx?.store?.id;

  const commands = buildCommands(storeId);

  /** Filter commands by query. */
  const filtered = query
    ? commands.filter((c) => {
        const search = query.toLowerCase();
        return (
          c.label.toLowerCase().includes(search) ||
          (c.keywords || "").toLowerCase().includes(search)
        );
      })
    : commands;

  /** Group filtered commands by section. */
  const sections: Record<string, CommandItem[]> = {};
  for (const item of filtered) {
    if (!sections[item.section]) sections[item.section] = [];
    sections[item.section].push(item);
  }

  /** Flatten for keyboard navigation. */
  const flatItems = Object.values(sections).flat();

  /** Execute a command. */
  const execute = useCallback(
    (item: CommandItem) => {
      setOpen(false);
      setQuery("");
      if (item.href) router.push(item.href);
      else if (item.action) item.action();
    },
    [router]
  );

  /** Global keyboard shortcut. */
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
        setQuery("");
        setSelected(0);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  /** Focus input when opened. */
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  /** Keyboard navigation within the palette. */
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, flatItems.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter" && flatItems[selected]) {
      e.preventDefault();
      execute(flatItems[selected]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />

      {/* Palette */}
      <div className="relative mx-auto mt-[15vh] max-w-lg">
        <div className="rounded-xl border border-border bg-background shadow-2xl overflow-hidden">
          {/* Search input */}
          <div className="flex items-center border-b border-border px-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-muted-foreground mr-2 shrink-0"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" x2="16.65" y1="21" y2="16.65" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelected(0);
              }}
              onKeyDown={handleKeyDown}
              placeholder="Search pages and actions..."
              className="flex-1 py-3 text-sm bg-transparent border-0 outline-none placeholder:text-muted-foreground"
            />
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] rounded border border-border text-muted-foreground">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-[50vh] overflow-y-auto p-2">
            {flatItems.length === 0 && (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No results found.
              </p>
            )}

            {Object.entries(sections).map(([section, items]) => (
              <div key={section}>
                <p className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                  {section}
                </p>
                {items.map((item) => {
                  const idx = flatItems.indexOf(item);
                  return (
                    <button
                      key={`${item.section}-${item.label}`}
                      type="button"
                      onClick={() => execute(item)}
                      onMouseEnter={() => setSelected(idx)}
                      className={`w-full text-left px-3 py-2 text-sm rounded-md transition-colors ${
                        idx === selected
                          ? "bg-primary/10 text-primary"
                          : "hover:bg-muted/50"
                      }`}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Footer hint */}
          <div className="border-t border-border px-4 py-2 flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground">
              Navigate with <kbd className="px-1 border rounded text-[9px]">↑</kbd> <kbd className="px-1 border rounded text-[9px]">↓</kbd> and <kbd className="px-1 border rounded text-[9px]">Enter</kbd>
            </span>
            <span className="text-[10px] text-muted-foreground">
              <kbd className="px-1 border rounded text-[9px]">⌘K</kbd> to toggle
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
