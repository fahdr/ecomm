/**
 * Footer component for the master suite landing page.
 *
 * Contains product links for all 8 services, company links, and legal info.
 *
 * **For Developers:**
 *   - Service links are generated from the `services` array in suite.config.ts.
 *   - Layout uses CSS grid for responsive columns.
 *
 * **For QA Engineers:**
 *   - Verify all 8 service links render and point to correct URLs.
 *   - Test responsive layout: stacked on mobile, grid on desktop.
 *
 * @returns The footer JSX element.
 */
import { services } from "@/suite.config";

export function Footer() {
  return (
    <footer className="border-t py-16" style={{ borderColor: "var(--color-border)" }}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-4">
          {/* Brand column */}
          <div>
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-[var(--color-brand)] to-[var(--color-accent-violet)]">
                <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <span className="font-bold" style={{ fontFamily: "var(--font-heading)" }}>
                DropShip Suite
              </span>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: "var(--color-text-muted)" }}>
              The complete AI-powered automation platform for modern dropshipping businesses.
            </p>
          </div>

          {/* Products column */}
          <div>
            <h4 className="mb-4 text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>
              Products
            </h4>
            <ul className="space-y-2">
              {services.slice(0, 4).map((svc) => (
                <li key={svc.slug}>
                  <a
                    href={svc.landingUrl}
                    className="text-sm transition-colors hover:text-[var(--color-brand)]"
                    style={{ color: "var(--color-text-muted)" }}
                  >
                    {svc.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* More products column */}
          <div>
            <h4 className="mb-4 text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>
              More Tools
            </h4>
            <ul className="space-y-2">
              {services.slice(4).map((svc) => (
                <li key={svc.slug}>
                  <a
                    href={svc.landingUrl}
                    className="text-sm transition-colors hover:text-[var(--color-brand)]"
                    style={{ color: "var(--color-text-muted)" }}
                  >
                    {svc.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Company column */}
          <div>
            <h4 className="mb-4 text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>
              Company
            </h4>
            <ul className="space-y-2">
              {["About", "Blog", "Careers", "Privacy Policy", "Terms of Service"].map((link) => (
                <li key={link}>
                  <a
                    href="#"
                    className="text-sm transition-colors hover:text-[var(--color-brand)]"
                    style={{ color: "var(--color-text-muted)" }}
                  >
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div
          className="mt-12 border-t pt-8 text-center text-sm"
          style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}
        >
          &copy; {new Date().getFullYear()} DropShip Suite. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
