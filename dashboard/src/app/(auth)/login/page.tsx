/**
 * Login page.
 *
 * Provides a form for users to sign in with their email and password.
 * On success, redirects to the dashboard home page.
 *
 * **For End Users:**
 *   Enter your registered email and password, then click "Sign in".
 *   If you don't have an account, click the "Register" link.
 *
 * **For QA Engineers:**
 *   - Invalid credentials show an error message below the form.
 *   - The submit button is disabled while the request is in flight.
 *   - Successful login redirects to `/`.
 *   - Card has glass-morphism effect with gradient mesh background.
 */

"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FadeIn } from "@/components/motion-wrappers";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function LoginPage() {
  const { login, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  /**
   * Handle form submission — call the auth context login function.
   */
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    await login(email, password);
    setSubmitting(false);
  }

  return (
    <FadeIn>
      <Card variant="glass">
        <CardHeader className="text-center">
          <CardTitle className="font-heading text-2xl">Sign in</CardTitle>
          <CardDescription>
            Enter your credentials to access the dashboard
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <p className="text-sm text-destructive text-center">{error}</p>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-4">
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Signing in..." : "Sign in"}
            </Button>
            <p className="text-sm text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="text-primary underline">
                Register
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </FadeIn>
  );
}
