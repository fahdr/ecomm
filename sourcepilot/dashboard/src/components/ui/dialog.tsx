/**
 * Dialog (modal) component built on @radix-ui/react-dialog.
 *
 * Provides an accessible modal overlay with backdrop dimming,
 * focus trapping, and keyboard dismissal (Escape key).
 *
 * **For Developers:**
 *   - Compound component pattern: Dialog > DialogTrigger + DialogContent.
 *   - DialogContent automatically renders a portal + overlay.
 *   - Close button is included by default (set showCloseButton=false to hide).
 *   - Import: `import { Dialog, DialogContent, DialogHeader, ... } from "@/components/ui/dialog"`
 *
 * **For QA Engineers:**
 *   - Verify Escape key closes the dialog.
 *   - Verify clicking outside the dialog (on the overlay) closes it.
 *   - Check focus is trapped within the dialog when open.
 *   - Test with screen readers for proper aria labels.
 *
 * **For End Users:**
 *   - Dialogs appear centered on screen with a dimmed background.
 *   - Press Escape or click outside to close.
 */

"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

/** Root dialog container — manages open/close state. */
const Dialog = DialogPrimitive.Root;

/** Element that triggers the dialog to open when clicked. */
const DialogTrigger = DialogPrimitive.Trigger;

/** Portal for rendering dialog outside the DOM hierarchy. */
const DialogPortal = DialogPrimitive.Portal;

/** Programmatic close trigger. */
const DialogClose = DialogPrimitive.Close;

/**
 * Dialog overlay — the semi-transparent backdrop behind the dialog.
 *
 * @param props - Radix overlay props plus className.
 * @returns A fixed-position overlay with fade animation.
 */
const DialogOverlay = React.forwardRef<
  React.ComponentRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-black/50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
  />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

/** Props for DialogContent, extending Radix content props. */
interface DialogContentProps
  extends React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
  /** Whether to show the X close button in the top-right corner. Default: true. */
  showCloseButton?: boolean;
}

/**
 * Dialog content panel — the centered card that contains the dialog body.
 * Renders inside a portal with an overlay backdrop.
 *
 * @param props - DialogContentProps.
 * @returns A centered, animated dialog panel.
 */
const DialogContent = React.forwardRef<
  React.ComponentRef<typeof DialogPrimitive.Content>,
  DialogContentProps
>(({ className, children, showCloseButton = true, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 rounded-lg",
        className
      )}
      {...props}
    >
      {children}
      {showCloseButton && (
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
          <X className="size-4" />
          <span className="sr-only">Close</span>
        </DialogPrimitive.Close>
      )}
    </DialogPrimitive.Content>
  </DialogPortal>
));
DialogContent.displayName = DialogPrimitive.Content.displayName;

/**
 * Dialog header — contains the title and optional description.
 *
 * @param props - Standard div props.
 * @returns A flex column for dialog header content.
 */
const DialogHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col space-y-1.5 text-center sm:text-left",
      className
    )}
    {...props}
  />
);
DialogHeader.displayName = "DialogHeader";

/**
 * Dialog footer — typically holds action buttons (Confirm, Cancel).
 *
 * @param props - Standard div props.
 * @returns A flex row for dialog action buttons.
 */
const DialogFooter = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2",
      className
    )}
    {...props}
  />
);
DialogFooter.displayName = "DialogFooter";

/**
 * Dialog title — the primary heading in the dialog header.
 *
 * @param props - Radix title props.
 * @returns A styled heading element.
 */
const DialogTitle = React.forwardRef<
  React.ComponentRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn(
      "text-lg font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
));
DialogTitle.displayName = DialogPrimitive.Title.displayName;

/**
 * Dialog description — secondary text explaining the dialog's purpose.
 *
 * @param props - Radix description props.
 * @returns A styled paragraph in muted foreground.
 */
const DialogDescription = React.forwardRef<
  React.ComponentRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
DialogDescription.displayName = DialogPrimitive.Description.displayName;

export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
};
