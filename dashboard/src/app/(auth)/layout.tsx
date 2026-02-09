/**
 * Layout for authentication pages (login, register).
 *
 * Renders a centered card layout with a gradient mesh background
 * and no navigation — a focused, premium auth experience.
 *
 * **For Developers:**
 *   This is a Next.js route group layout. The `(auth)` folder does not
 *   appear in the URL path — `/login` and `/register` are top-level routes.
 *   The bg-gradient-mesh class is defined in globals.css.
 *
 * **For End Users:**
 *   This layout provides a simple, distraction-free experience for
 *   signing in or creating an account.
 */

import { ThemeToggle } from "@/components/theme-toggle";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-mesh bg-background px-4">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
