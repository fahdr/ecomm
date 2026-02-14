/**
 * Card component family for content grouping and visual hierarchy.
 *
 * Follows the shadcn/ui compound component pattern: Card wraps CardHeader,
 * CardTitle, CardDescription, CardContent, and CardFooter.
 *
 * **For Developers:**
 *   - Card uses `bg-card` for theme-aware background colors.
 *   - All sub-components use consistent px-6 horizontal padding.
 *   - Import: `import { Card, CardHeader, CardTitle, CardContent } from "@ecomm/ui-kit"`
 *
 * **For QA Engineers:**
 *   - Verify card borders and shadows are visible in both light and dark mode.
 *   - Check that CardContent does not overflow its container.
 *
 * **For End Users:**
 *   - Cards group related information into visually distinct sections.
 */

import * as React from "react";
import { cn } from "../../lib/utils";

/** Card container — outer wrapper with background, border, and shadow. */
const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm",
      className
    )}
    {...props}
  />
));
Card.displayName = "Card";

/** Card header section — contains title, description, and optional action slot. */
const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col gap-1.5 px-6", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

/** Card title — primary heading text within a card. */
const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn("leading-none font-semibold tracking-tight", className)}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

/** Card description — secondary text beneath the title. */
const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-muted-foreground text-sm", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

/** Card content — main body area. */
const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("px-6", className)} {...props} />
));
CardContent.displayName = "CardContent";

/** Card footer — bottom section for action buttons. */
const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center px-6", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter };
