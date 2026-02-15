/**
 * Login page — email/password authentication form.
 *
 * Presents a branded login form on a gradient mesh background.
 * On successful login, stores the JWT token and redirects to the dashboard.
 *
 * **For Developers:**
 *   - Calls `POST /api/v1/auth/login` with `{ email, password }`.
 *   - Expects response shape: `{ access_token: string, user: { email: string } }`.
 *   - On success, sets token via `setToken()` and email via `setUserEmail()`.
 *   - Redirects to "/" after successful auth.
 *   - Error messages from the API are displayed below the form.
 *
 * **For Project Managers:**
 *   - This is the entry point for all users — it must be visually polished.
 *   - The gradient mesh background uses the service's primary/accent colors.
 *   - Service name and tagline are displayed prominently.
 *
 * **For QA Engineers:**
 *   - Test with valid credentials — should redirect to dashboard.
 *   - Test with invalid credentials — should show error message.
 *   - Test with empty fields — should show client-side validation.
 *   - Test the "Register" link navigates to /register.
 *   - Verify the form works in both light and dark mode.
 *   - Check password field has type="password" (masked input).
 *
 * **For End Users:**
 *   - Enter your email and password to access the dashboard.
 *   - If you don't have an account, click "Register" to create one.
 */

"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { FadeIn } from "@/components/motion";
import { api } from "@/lib/api";
import { setToken, setUserEmail, isAuthenticated } from "@/lib/auth";
import { serviceConfig } from "@/service.config";

/** Expected response shape from POST /api/v1/auth/login. */
interface LoginResponse {
  access_token: string;
  user: { email: string };
}

/**
 * Login page component.
 *
 * @returns The login page with branded form on gradient background.
 */
export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
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
   * Validates inputs, calls the login API, stores the token, and redirects.
   *
   * @param e - The form submit event.
   */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password.trim()) {
      setError("Please fill in all fields.");
      return;
    }

    setLoading(true);

    const { data, error: apiError } = await api.post<LoginResponse>(
      "/api/v1/auth/login",
      { email, password }
    );

    setLoading(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    if (data) {
      setToken(data.access_token);
      setUserEmail(email);
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
              Sign in to {serviceConfig.name}
            </CardTitle>
            <CardDescription>
              {serviceConfig.tagline}
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email Field */}
              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="text-sm font-medium leading-none"
                >
                  Email
                </label>
                <Input
                  id="email"
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
                  htmlFor="password"
                  className="text-sm font-medium leading-none"
                >
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
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
                {loading && <Loader2 className="size-4 animate-spin" />}
                {loading ? "Signing in..." : "Sign in"}
              </Button>
            </form>

            {/* Register Link */}
            <div className="mt-6 text-center text-sm text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link
                href="/register"
                className="text-primary font-medium hover:underline underline-offset-4"
              >
                Register
              </Link>
            </div>
          </CardContent>
        </Card>
      </FadeIn>
    </div>
  );
}
