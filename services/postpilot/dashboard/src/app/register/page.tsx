/**
 * Registration page — create a new account with email and password.
 *
 * Presents a branded registration form on a gradient mesh background.
 * On successful registration, stores the JWT token and redirects to the dashboard.
 *
 * **For Developers:**
 *   - Calls `POST /api/v1/auth/register` with `{ email, password }`.
 *   - Includes client-side password confirmation validation.
 *   - Expects response shape: `{ access_token: string, user: { email: string } }`.
 *   - On success, sets token and redirects to "/".
 *
 * **For Project Managers:**
 *   - Registration is the growth funnel entry — it should be frictionless.
 *   - The form mirrors the login page design for visual consistency.
 *
 * **For QA Engineers:**
 *   - Test with valid inputs — should create account and redirect.
 *   - Test with mismatched passwords — should show validation error.
 *   - Test with duplicate email — should show API error message.
 *   - Test with very short password — should show API validation error.
 *   - Verify the "Sign in" link navigates to /login.
 *
 * **For End Users:**
 *   - Fill in your email and choose a password to create an account.
 *   - If you already have an account, click "Sign in" to log in.
 */

"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { FadeIn } from "@/components/motion";
import { api } from "@/lib/api";
import { setToken, setUserEmail, isAuthenticated } from "@/lib/auth";
import { serviceConfig } from "@/service.config";

/** Expected response shape from POST /api/v1/auth/register. */
interface RegisterResponse {
  access_token: string;
  user: { email: string };
}

/**
 * Registration page component.
 *
 * @returns The registration page with branded form on gradient background.
 */
export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  /* Redirect to dashboard if already authenticated */
  React.useEffect(() => {
    if (isAuthenticated()) {
      router.replace("/");
    }
  }, [router]);

  /**
   * Handle form submission.
   * Validates inputs (including password confirmation), calls the register API,
   * stores the token, and redirects to the dashboard.
   *
   * @param e - The form submit event.
   */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    /* Client-side validation */
    if (!email.trim() || !password.trim() || !confirmPassword.trim()) {
      setError("Please fill in all fields.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);

    const { data, error: apiError } = await api.post<RegisterResponse>(
      "/api/v1/auth/register",
      { email, password }
    );

    setLoading(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    if (data) {
      setToken(data.access_token);
      setUserEmail(data.user.email);
      router.push("/");
    }
  }

  return (
    <div className="min-h-screen bg-gradient-mesh flex items-center justify-center p-4">
      <FadeIn direction="up" duration={0.6}>
        <Card className="w-full max-w-md shadow-xl border-border/50">
          <CardHeader className="text-center">
            {/* Service Logo */}
            <div className="mx-auto mb-4 size-14 rounded-xl bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-2xl font-heading">
                {serviceConfig.name.charAt(0)}
              </span>
            </div>
            <CardTitle className="font-heading text-2xl">
              Create your account
            </CardTitle>
            <CardDescription>
              Get started with {serviceConfig.name}
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email Field */}
              <div className="space-y-2">
                <label
                  htmlFor="register-email"
                  className="text-sm font-medium leading-none"
                >
                  Email
                </label>
                <Input
                  id="register-email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                />
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <label
                  htmlFor="register-password"
                  className="text-sm font-medium leading-none"
                >
                  Password
                </label>
                <Input
                  id="register-password"
                  type="password"
                  placeholder="At least 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>

              {/* Confirm Password Field */}
              <div className="space-y-2">
                <label
                  htmlFor="register-confirm"
                  className="text-sm font-medium leading-none"
                >
                  Confirm Password
                </label>
                <Input
                  id="register-confirm"
                  type="password"
                  placeholder="Re-enter your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>

              {/* Error Message */}
              {error && (
                <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
                  <p className="text-sm text-destructive">{error}</p>
                </div>
              )}

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full"
                disabled={loading}
              >
                {loading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <UserPlus className="size-4" />
                )}
                {loading ? "Creating account..." : "Create account"}
              </Button>
            </form>

            {/* Login Link */}
            <div className="mt-6 text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link
                href="/login"
                className="text-primary font-medium hover:underline underline-offset-4"
              >
                Sign in
              </Link>
            </div>
          </CardContent>
        </Card>
      </FadeIn>
    </div>
  );
}
