/**
 * Breadcrumb navigation component for the dashboard.
 *
 * Renders a horizontal trail of links showing the current page hierarchy.
 * Used in the dashboard shell's top bar to provide contextual navigation.
 *
 * **For Developers:**
 *   - Pass an array of { label, href? } items
 *   - The last item is rendered as plain text (current page)
 *   - All other items are rendered as clickable links
 *
 * **For QA:**
 *   - Breadcrumbs should reflect the current page hierarchy
 *   - All links except the last should be clickable
 *   - Separator "/" should appear between items
 */

import Link from "next/link";
import { ChevronRight } from "lucide-react";

/** A single breadcrumb item with a label and optional link. */
export interface BreadcrumbItem {
  /** Display text for this breadcrumb. */
  label: string;
  /** Optional URL — if omitted, rendered as plain text (current page). */
  href?: string;
}

/**
 * Renders a horizontal breadcrumb trail.
 *
 * @param items - Ordered array of breadcrumb items from root to current page.
 * @returns A nav element with breadcrumb links and separators.
 */
export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;

        return (
          <span key={index} className="flex items-center gap-1.5">
            {index > 0 && (
              <ChevronRight className="size-3.5 text-muted-foreground/60" />
            )}
            {isLast || !item.href ? (
              <span className="font-medium text-foreground">{item.label}</span>
            ) : (
              <Link
                href={item.href}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {item.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
