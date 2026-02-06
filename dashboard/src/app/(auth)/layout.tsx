/**
 * Layout for authentication pages (login, register).
 *
 * Renders a centered card layout without navigation — a clean,
 * focused UI for the auth forms.
 *
 * **For Developers:**
 *   This is a Next.js route group layout. The `(auth)` folder does not
 *   appear in the URL path — `/login` and `/register` are top-level routes.
 *
 * **For End Users:**
 *   This layout provides a simple, distraction-free experience for
 *   signing in or creating an account.
 */

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
