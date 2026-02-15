/**
 * Reusable empty state component for pages with no data.
 *
 * Displays a centered icon, title, optional description, and optional
 * call-to-action button. Used across the dashboard for consistent
 * empty state messaging.
 *
 * **For Developers:**
 *   - Pass a lucide-react icon component as the `icon` prop
 *   - The `action` prop renders a button/link below the description
 *   - All text is centered and uses muted colors
 *
 * **For QA:**
 *   - Should appear when a list/table has zero items
 *   - CTA button (if provided) should work correctly
 *   - Layout should be centered both horizontally and vertically
 *
 * **For End Users:**
 *   Empty states provide guidance on what to do next when a section
 *   has no data yet, such as creating your first product or order.
 */

import { cn } from "@/lib/utils";

/**
 * Renders a centered empty state with icon, title, description, and action.
 *
 * @param icon - A React element for the icon (e.g., from lucide-react).
 * @param title - Headline text for the empty state.
 * @param description - Optional explanatory text below the title.
 * @param action - Optional React element (typically a Button or Link).
 * @param className - Optional additional CSS classes.
 * @returns A centered empty state layout.
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 py-16 text-center",
        className
      )}
    >
      <div className="flex size-14 items-center justify-center rounded-xl bg-muted text-muted-foreground">
        {icon}
      </div>
      <div className="space-y-1.5">
        <h3 className="font-heading text-lg font-semibold">{title}</h3>
        {description && (
          <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
