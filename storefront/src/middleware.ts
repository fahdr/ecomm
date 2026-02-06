/**
 * Next.js middleware for store slug resolution.
 *
 * Runs on every request to extract the store slug from either the ``?store=``
 * query parameter (local dev) or the subdomain (production). The resolved
 * slug is forwarded to pages via a custom request header
 * (``x-store-slug``).
 *
 * **For Developers:**
 *   The slug is set as a header rather than a cookie because middleware
 *   runs on the edge and headers are the simplest way to pass data to
 *   server components. Pages read it via ``headers()`` from ``next/headers``.
 *
 * **For QA Engineers:**
 *   - Requests without a resolvable slug still proceed (the page handles
 *     the missing-store case by showing a 404).
 *   - Static assets (``_next/``, ``favicon.ico``) are excluded from
 *     middleware processing.
 */

import { NextRequest, NextResponse } from "next/server";
import { resolveSlug } from "@/lib/store";

/**
 * Middleware function that extracts the store slug and forwards it as a header.
 *
 * @param request - The incoming Next.js request.
 * @returns A NextResponse with the ``x-store-slug`` header set if a slug was resolved.
 */
export function middleware(request: NextRequest): NextResponse {
  const slug = resolveSlug(request.url);

  const requestHeaders = new Headers(request.headers);
  if (slug) {
    requestHeaders.set("x-store-slug", slug);
  }

  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
}

/**
 * Middleware matcher configuration — skip static assets and internal routes.
 */
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
