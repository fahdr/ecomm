/**
 * Next.js middleware for store slug resolution.
 *
 * Runs on every request to extract the store slug from either the ``?store=``
 * query parameter (local dev), a persisted cookie, or the subdomain
 * (production). The resolved slug is forwarded to pages via a custom
 * request header (``x-store-slug``).
 *
 * **For Developers:**
 *   The slug is set as a header so server components can read it via
 *   ``headers()`` from ``next/headers``. When resolved from a ``?store=``
 *   query param, the slug is also saved to a ``store-slug`` cookie so
 *   that client-side navigations (which lose the query param) continue
 *   to resolve the correct store.
 *
 * **For QA Engineers:**
 *   - Requests without a resolvable slug still proceed (the page handles
 *     the missing-store case by showing a 404).
 *   - Static assets (``_next/``, ``favicon.ico``) are excluded from
 *     middleware processing.
 *   - The ``store-slug`` cookie is ``SameSite=Lax`` and lasts 24 hours.
 */

import { NextRequest, NextResponse } from "next/server";
import { resolveSlug } from "@/lib/store";

/** Cookie name used to persist the store slug across navigations. */
const STORE_COOKIE = "store-slug";

/**
 * Middleware function that extracts the store slug and forwards it as a header.
 *
 * Resolution order:
 *   1. ``?store=`` query parameter (highest priority)
 *   2. ``store-slug`` cookie (persisted from a previous request)
 *   3. Subdomain (production)
 *
 * When the slug comes from the query param, it is saved to a cookie so
 * that subsequent client-side navigations (e.g. Next.js ``<Link>``) can
 * still resolve the store without the query param in the URL.
 *
 * @param request - The incoming Next.js request.
 * @returns A NextResponse with the ``x-store-slug`` header set if a slug was resolved.
 */
export function middleware(request: NextRequest): NextResponse {
  // Try resolving from query param or subdomain first.
  let slug = resolveSlug(request.url);
  let slugFromQuery = !!slug;

  // Fall back to the cookie if no slug was resolved.
  if (!slug) {
    slug = request.cookies.get(STORE_COOKIE)?.value ?? null;
    slugFromQuery = false;
  }

  const requestHeaders = new Headers(request.headers);
  if (slug) {
    requestHeaders.set("x-store-slug", slug);
  }

  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  // Persist the slug to a cookie when it came from the query param.
  if (slug && slugFromQuery) {
    response.cookies.set(STORE_COOKIE, slug, {
      path: "/",
      maxAge: 60 * 60 * 24, // 24 hours
      sameSite: "lax",
      httpOnly: false,
    });
  }

  return response;
}

/**
 * Middleware matcher configuration — skip static assets and internal routes.
 */
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
