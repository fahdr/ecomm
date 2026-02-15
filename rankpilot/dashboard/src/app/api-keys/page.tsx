/**
 * API Keys page — create, view, copy, and revoke API keys.
 *
 * Provides full CRUD for API keys used to authenticate external integrations
 * with the service backend. Keys are shown in a table with metadata like
 * prefix, name, scopes, last used timestamp, and creation date.
 *
 * **For Developers:**
 *   - `GET /api/v1/api-keys` — list all keys (returns prefix, not full key).
 *   - `POST /api/v1/api-keys` — create a new key `{ name, scopes: string[] }`.
 *     Response includes the full key ONCE — it cannot be retrieved again.
 *   - `DELETE /api/v1/api-keys/:id` — revoke a key permanently.
 *   - The "Create Key" flow uses a Dialog modal for name + scopes input.
 *   - After creation, the full key is displayed in a copyable field with a
 *     prominent "shown once" warning.
 *
 * **For Project Managers:**
 *   - API keys are the primary integration mechanism for developers using the service.
 *   - The "shown once" pattern is a security best practice (like GitHub tokens).
 *   - Scopes can be extended per service (e.g. "read", "write", "admin").
 *
 * **For QA Engineers:**
 *   - Verify creating a key shows the full key exactly once.
 *   - Verify the copy button copies the key to clipboard.
 *   - Verify revoking a key removes it from the list.
 *   - Test the revoke confirmation dialog appears before deletion.
 *   - Verify empty state is shown when no keys exist.
 *   - Test creating a key with no name — should show validation error.
 *
 * **For End Users:**
 *   - API keys let you connect external tools and scripts to your account.
 *   - When you create a key, copy it immediately — it will not be shown again.
 *   - Revoke keys you no longer need to keep your account secure.
 */

"use client";

import * as React from "react";
import {
  Plus,
  Copy,
  Trash2,
  Check,
  AlertTriangle,
  Key,
  Loader2,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { FadeIn, StaggerChildren, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";

/** Shape of an API key as returned by the list endpoint. */
interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  last_used: string | null;
  created_at: string;
}

/** Shape of the create API key response (includes the full key). */
interface CreateApiKeyResponse {
  id: string;
  name: string;
  key: string;
  prefix: string;
  scopes: string[];
  created_at: string;
}

/**
 * API Keys page component.
 *
 * @returns The API keys management page wrapped in the Shell layout.
 */
export default function ApiKeysPage() {
  const [keys, setKeys] = React.useState<ApiKey[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* Create key dialog state */
  const [createOpen, setCreateOpen] = React.useState(false);
  const [newKeyName, setNewKeyName] = React.useState("");
  const [newKeyScopes, setNewKeyScopes] = React.useState("read,write");
  const [creating, setCreating] = React.useState(false);

  /* Newly created key display */
  const [createdKey, setCreatedKey] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState(false);

  /* Revoke confirmation */
  const [revokeTarget, setRevokeTarget] = React.useState<ApiKey | null>(null);
  const [revoking, setRevoking] = React.useState(false);

  /**
   * Fetch all API keys on mount.
   */
  React.useEffect(() => {
    fetchKeys();
  }, []);

  /**
   * Fetch the list of API keys from the backend.
   */
  async function fetchKeys() {
    setLoading(true);
    const { data, error: apiError } = await api.get<ApiKey[]>("/api/v1/api-keys");
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setKeys(data);
    }
    setLoading(false);
  }

  /**
   * Create a new API key with the provided name and scopes.
   * Displays the full key in a copyable field after creation.
   */
  async function handleCreateKey() {
    if (!newKeyName.trim()) {
      setError("Please enter a name for the API key.");
      return;
    }

    setCreating(true);
    setError(null);

    const scopes = newKeyScopes
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const { data, error: apiError } = await api.post<CreateApiKeyResponse>(
      "/api/v1/api-keys",
      { name: newKeyName.trim(), scopes }
    );

    setCreating(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    if (data) {
      setCreatedKey(data.key);
      setCreateOpen(false);
      setNewKeyName("");
      setNewKeyScopes("read,write");
      fetchKeys();
    }
  }

  /**
   * Copy the newly created key to the clipboard.
   */
  async function handleCopyKey() {
    if (createdKey) {
      await navigator.clipboard.writeText(createdKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  /**
   * Revoke (permanently delete) an API key.
   *
   * @param id - The API key ID to revoke.
   */
  async function handleRevokeKey(id: string) {
    setRevoking(true);
    const { error: apiError } = await api.del(`/api/v1/api-keys/${id}`);
    setRevoking(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setRevokeTarget(null);
    fetchKeys();
  }

  /**
   * Format a date string for display.
   *
   * @param dateStr - ISO date string.
   * @returns Formatted date or "Never" for null.
   */
  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                API Keys
              </h2>
              <p className="text-muted-foreground mt-1">
                Create and manage API keys for external integrations.
              </p>
            </div>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="size-4" />
              Create Key
            </Button>
          </div>
        </FadeIn>

        {/* ── Newly Created Key Banner ── */}
        {createdKey && (
          <FadeIn>
            <Card className="border-amber-500/50 bg-amber-50 dark:bg-amber-950/20">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="size-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                  <div className="flex-1 space-y-3">
                    <div>
                      <p className="font-medium text-amber-900 dark:text-amber-200">
                        API key created successfully
                      </p>
                      <p className="text-sm text-amber-800 dark:text-amber-300 mt-1">
                        Copy this key now. It will not be shown again.
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 bg-white dark:bg-black/30 rounded-md border border-amber-300 dark:border-amber-700 px-3 py-2 text-sm font-mono break-all">
                        {createdKey}
                      </code>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={handleCopyKey}
                        className="shrink-0 border-amber-300 dark:border-amber-700"
                      >
                        {copied ? (
                          <Check className="size-4 text-emerald-600" />
                        ) : (
                          <Copy className="size-4" />
                        )}
                      </Button>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setCreatedKey(null)}
                      className="text-amber-700 dark:text-amber-300"
                    >
                      Dismiss
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* ── Keys List ── */}
        {loading ? (
          <Card>
            <CardContent className="pt-6 space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-9 w-9 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-48" />
                  </div>
                  <Skeleton className="h-8 w-20" />
                </div>
              ))}
            </CardContent>
          </Card>
        ) : keys.length === 0 ? (
          <FadeIn>
            <Card>
              <CardContent className="pt-12 pb-12 text-center">
                <div className="mx-auto size-12 rounded-full bg-muted flex items-center justify-center mb-4">
                  <Key className="size-6 text-muted-foreground" />
                </div>
                <h3 className="font-heading font-semibold text-lg">
                  No API keys yet
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                  Create your first API key to start integrating with the API.
                </p>
                <Button className="mt-4" onClick={() => setCreateOpen(true)}>
                  <Plus className="size-4" />
                  Create your first key
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <StaggerChildren className="space-y-3" staggerDelay={0.05}>
            {keys.map((key) => (
              <Card key={key.id} className="py-4">
                <CardContent className="flex items-center gap-4">
                  {/* Key Icon */}
                  <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <Key className="size-5 text-primary" />
                  </div>

                  {/* Key Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium truncate">{key.name}</p>
                      {key.scopes.map((scope) => (
                        <Badge key={scope} variant="secondary" className="text-xs">
                          {scope}
                        </Badge>
                      ))}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                      <code className="font-mono">{key.prefix}...****</code>
                      <span>Created {formatDate(key.created_at)}</span>
                      <span>Last used {formatDate(key.last_used)}</span>
                    </div>
                  </div>

                  {/* Revoke Button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground hover:text-destructive shrink-0"
                    onClick={() => setRevokeTarget(key)}
                  >
                    <Trash2 className="size-4" />
                    <span className="hidden sm:inline">Revoke</span>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </StaggerChildren>
        )}

        {/* ── Error Message ── */}
        {error && (
          <FadeIn>
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </FadeIn>
        )}

        {/* ── Create Key Dialog ── */}
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create API Key</DialogTitle>
              <DialogDescription>
                Create a new API key for external integrations. The full key
                will only be shown once after creation.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Key Name */}
              <div className="space-y-2">
                <label htmlFor="key-name" className="text-sm font-medium">
                  Key Name
                </label>
                <Input
                  id="key-name"
                  placeholder="e.g. Production Server"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                />
              </div>

              {/* Scopes */}
              <div className="space-y-2">
                <label htmlFor="key-scopes" className="text-sm font-medium">
                  Scopes
                </label>
                <Input
                  id="key-scopes"
                  placeholder="read,write"
                  value={newKeyScopes}
                  onChange={(e) => setNewKeyScopes(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated list of permission scopes.
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setCreateOpen(false)}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button onClick={handleCreateKey} disabled={creating}>
                {creating && <Loader2 className="size-4 animate-spin" />}
                {creating ? "Creating..." : "Create Key"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Revoke Confirmation Dialog ── */}
        <Dialog
          open={revokeTarget !== null}
          onOpenChange={(open) => {
            if (!open) setRevokeTarget(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Revoke API Key</DialogTitle>
              <DialogDescription>
                Are you sure you want to revoke the key{" "}
                <strong>&quot;{revokeTarget?.name}&quot;</strong>? This action
                cannot be undone. Any integrations using this key will stop
                working immediately.
              </DialogDescription>
            </DialogHeader>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setRevokeTarget(null)}
                disabled={revoking}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => revokeTarget && handleRevokeKey(revokeTarget.id)}
                disabled={revoking}
              >
                {revoking && <Loader2 className="size-4 animate-spin" />}
                {revoking ? "Revoking..." : "Revoke Key"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
