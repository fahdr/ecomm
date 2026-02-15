/**
 * Next.js proxy (route protection).
 *
 * Runs on every navigation to check whether the user has an access token
 * cookie. Unauthenticated users are redirected to `/login`, and
 * authenticated users visiting `/login` or `/register` are redirected
 * to `/`.
 *
 * **For Developers:**
 *   This proxy runs on the Edge runtime and only checks for the
 *   *presence* of the `access_token` cookie — it does not validate the
 *   JWT. Full validation happens client-side in the `AuthProvider`.
 *
 * **For QA Engineers:**
 *   - Deleting the `access_token` cookie and navigating will redirect
 *     to `/login`.
 *   - Visiting `/login` while authenticated redirects to `/`.
 */

import { NextRequest, NextResponse } from "next/server";

/** Routes that do not require authentication. */
const PUBLIC_PATHS = ["/login", "/register"];

/**
 * Proxy function that protects routes based on authentication status.
 *
 * @param request - The incoming Next.js request.
 * @returns A redirect response or the original request to continue.
 */
export function proxy(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const hasToken = request.cookies.has("access_token");

  const isPublicPath = PUBLIC_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`)
  );

  // Unauthenticated user trying to access a protected route → redirect to login.
  if (!hasToken && !isPublicPath) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  // Authenticated user trying to access login/register → redirect to home.
  if (hasToken && isPublicPath) {
    const homeUrl = new URL("/", request.url);
    return NextResponse.redirect(homeUrl);
  }

  return NextResponse.next();
}

/**
 * Matcher configuration — proxy runs on all routes except static
 * assets and Next.js internals.
 */
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
