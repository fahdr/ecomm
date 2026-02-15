/**
 * Admin login page for the Super Admin Dashboard.
 *
 * Provides a dark-themed login form with email/password fields.
 * Supports two modes:
 *   1. Normal login: Calls POST /auth/login with email + password.
 *   2. First-time setup: Calls POST /auth/setup when no admin exists.
 *
 * For Developers:
 *   The page checks for an existing admin by attempting a GET to
 *   /auth/status. If none exists, it shows setup mode with an
 *   additional "Name" field. On success, the JWT is stored and
 *   the user is redirected to /.
 *
 * For QA Engineers:
 *   - Test login with valid and invalid credentials.
 *   - Test first-time setup flow (requires empty admin table).
 *   - Verify error messages display correctly.
 *   - Verify redirect to / after successful login.
 *
 * For Project Managers:
 *   This is the entry point for admin access. The first-time
 *   setup flow eliminates the need for manual DB seeding.
 *
 * For End Users:
 *   This page is exclusively for platform administrators.
 */

"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Shield, Eye, EyeOff, Loader2 } from "lucide-react";
import * as motion from "motion/react-client";
import { adminApi } from "@/lib/api";

/**
 * Admin login page component.
 *
 * Renders a centered login card with email/password fields.
 * Detects whether the platform needs initial setup and adjusts
 * the form accordingly.
 *
 * @returns The login page JSX.
 */
export default function LoginPage() {
  const router = useRouter();

  /** Whether this is a first-time setup (no admins exist yet). */
  const [isSetupMode, setIsSetupMode] = useState(false);

  /** Whether the setup/login mode check is still loading. */
  const [checking, setChecking] = useState(true);

  /** Form field values. */
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");

  /** Whether the password field is visible. */
  const [showPassword, setShowPassword] = useState(false);

  /** Whether the form is currently submitting. */
  const [loading, setLoading] = useState(false);

  /** Error message to display (null if no error). */
  const [error, setError] = useState<string | null>(null);

  /**
   * On mount, check if the admin backend is set up.
   * If the user is already authenticated, redirect to /.
   * If no admins exist, enable setup mode.
   */
  useEffect(() => {
    /* If already authenticated, skip login. */
    if (adminApi.isAuthenticated()) {
      router.replace("/");
      return;
    }

    /* Check whether any admin accounts exist. */
    async function checkSetup() {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_ADMIN_API_URL || "http://localhost:8300/api/v1/admin"}/auth/status`
        );
        if (response.ok) {
          const data = await response.json();
          setIsSetupMode(!data.has_admin);
        }
      } catch {
        /* Backend might be unreachable; default to login mode. */
      } finally {
        setChecking(false);
      }
    }

    checkSetup();
  }, [router]);

  /**
   * Handle form submission for login or setup.
   *
   * @param e - The form submit event.
   */
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isSetupMode) {
        await adminApi.setup(email, password, name);
      } else {
        await adminApi.login(email, password);
      }
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  /* Show a loading spinner while checking setup status. */
  if (checking) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-6 h-6 border-2 border-[var(--admin-primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="w-full max-w-sm"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[var(--admin-primary-glow)] border border-[var(--admin-border-subtle)] mb-4">
            <Shield size={28} className="text-[var(--admin-primary)]" />
          </div>
          <h1 className="text-xl font-semibold text-[var(--admin-text-primary)] tracking-tight">
            {isSetupMode ? "Create Admin Account" : "Admin Login"}
          </h1>
          <p className="text-sm text-[var(--admin-text-muted)] mt-1.5">
            {isSetupMode
              ? "Set up the first administrator account"
              : "Sign in to the platform admin dashboard"}
          </p>
        </div>

        {/* Form card */}
        <div className="admin-card p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name field (setup mode only) */}
            {isSetupMode && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                transition={{ duration: 0.3 }}
              >
                <label
                  htmlFor="name"
                  className="block text-xs font-medium text-[var(--admin-text-secondary)] mb-1.5 uppercase tracking-wider"
                >
                  Name
                </label>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Admin Name"
                  className="admin-input"
                  required
                  autoComplete="name"
                />
              </motion.div>
            )}

            {/* Email field */}
            <div>
              <label
                htmlFor="email"
                className="block text-xs font-medium text-[var(--admin-text-secondary)] mb-1.5 uppercase tracking-wider"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@platform.io"
                className="admin-input"
                required
                autoComplete="email"
                autoFocus
              />
            </div>

            {/* Password field */}
            <div>
              <label
                htmlFor="password"
                className="block text-xs font-medium text-[var(--admin-text-secondary)] mb-1.5 uppercase tracking-wider"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className="admin-input pr-10"
                  required
                  autoComplete={
                    isSetupMode ? "new-password" : "current-password"
                  }
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--admin-text-muted)] hover:text-[var(--admin-text-secondary)] transition-colors"
                  tabIndex={-1}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Error message */}
            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-sm text-[var(--admin-danger)] bg-[oklch(0.63_0.22_25_/_0.08)] border border-[oklch(0.63_0.22_25_/_0.2)] rounded-lg px-3 py-2"
              >
                {error}
              </motion.div>
            )}

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading}
              className="admin-btn-primary w-full flex items-center justify-center gap-2 mt-2"
            >
              {loading && (
                <Loader2 size={16} className="animate-spin" />
              )}
              {isSetupMode ? "Create Account" : "Sign In"}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-[10px] text-[var(--admin-text-muted)] mt-6 uppercase tracking-widest">
          ecomm Platform Administration
        </p>
      </motion.div>
    </div>
  );
}
