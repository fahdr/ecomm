/**
 * Badge component for status indicators, labels, and tags.
 *
 * **For Developers:**
 *   - Variants: default (primary color), secondary (muted), destructive (red),
 *     outline (bordered), success (green).
 *   - Badges are inline-flex with rounded-full for pill shape.
 *   - Import: `import { Badge } from "@/components/ui/badge"`
 *
 * **For QA Engineers:**
 *   - Verify each variant is visually distinct and readable.
 *   - Test with long text to ensure badges truncate or wrap gracefully.
 *   - Check contrast ratios meet WCAG AA in both themes.
 *
 * **For End Users:**
 *   - Badges indicate status (active, expired) or categorize items (plan tier).
 */

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * CVA definition for badge style variants.
 * Base styles include pill shape, small text, and subtle border.
 */
const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border-transparent bg-destructive text-white",
        outline:
          "text-foreground",
        success:
          "border-transparent bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

/** Props for the Badge component. */
export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

/**
 * Badge component for displaying status labels and tags.
 *
 * @param props - BadgeProps including variant and standard div attrs.
 * @returns A styled inline element with pill shape.
 *
 * @example
 * <Badge variant="success">Active</Badge>
 * <Badge variant="destructive">Expired</Badge>
 * <Badge variant="outline">Free Tier</Badge>
 */
function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
