/**
 * Registration page.
 *
 * Provides a form for new users to create an account with email and
 * password. On success, the user is automatically logged in and
 * redirected to the dashboard home page.
 *
 * **For End Users:**
 *   Choose an email and a password (at least 8 characters) to create
 *   your account. You'll be signed in automatically.
 *
 * **For QA Engineers:**
 *   - Duplicate email shows an error message.
 *   - Password must be at least 8 characters (validated by the backend).
 *   - The submit button is disabled while the request is in flight.
 *   - Successful registration redirects to `/`.
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

export default function RegisterPage() {
  const { register, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  /**
   * Handle form submission — call the auth context register function.
   */
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    await register(email, password);
    setSubmitting(false);
  }

  return (
    <FadeIn>
      <Card variant="glass">
        <CardHeader className="text-center">
          <CardTitle className="font-heading text-2xl">Create an account</CardTitle>
          <CardDescription>
            Enter your details to get started
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
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-4">
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Creating account..." : "Create account"}
            </Button>
            <p className="text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link href="/login" className="text-primary underline">
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </FadeIn>
  );
}
