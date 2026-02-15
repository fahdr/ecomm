/**
 * Customer Segments management page.
 *
 * Lists all customer segments for a store and provides a form to create
 * new segments. Segments group customers by criteria (manual or automatic)
 * for targeted marketing and analytics.
 *
 * **For End Users:**
 *   Create customer segments to organize your buyers into groups such as
 *   "VIP Customers", "First-Time Buyers", or "Inactive 30 Days".
 *   Use segments for targeted email campaigns and discount offers.
 *
 * **For Developers:**
 *   - Fetches segments via `GET /api/v1/stores/{store_id}/segments`.
 *   - Creates new segments via `POST /api/v1/stores/{store_id}/segments`.
 *   - Segment types: "manual" (hand-picked) or "automatic" (rule-based).
 *
 * **For QA Engineers:**
 *   - Verify the segment list refreshes after creating a new segment.
 *   - Verify that the type selector defaults to "manual".
 *   - Verify that customer count displays correctly for each segment.
 *   - Verify the empty state is shown when no segments exist.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 19 (Segments) in the backlog.
 *   Customer segmentation enables targeted marketing workflows.
 */

"use client";

import { FormEvent, useEffect, useState, use } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

/** Shape of a customer segment returned by the API. */
interface Segment {
  id: string;
  name: string;
  description: string | null;
  segment_type: "manual" | "dynamic";
  customer_count: number;
  created_at: string;
  updated_at: string;
}

/**
 * SegmentsPage renders the customer segment listing and creation dialog.
 *
 * @param params - Route parameters containing the store ID.
 * @returns The rendered segments management page.
 */
export default function SegmentsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user, loading: authLoading } = useAuth();
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Create form state */
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formType, setFormType] = useState<"manual" | "dynamic">("manual");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  /**
   * Fetch all segments for this store.
   */
  async function fetchSegments() {
    setLoading(true);
    const result = await api.get<{ items: Segment[]; total: number }>(
      `/api/v1/stores/${id}/segments`
    );
    if (result.error) {
      setError(result.error.message);
    } else {
      setSegments(result.data?.items ?? []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchSegments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, user, authLoading]);

  /**
   * Handle the create-segment form submission.
   *
   * @param e - The form submission event.
   */
  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    const result = await api.post<Segment>(
      `/api/v1/stores/${id}/segments`,
      {
        name: formName,
        description: formDescription || null,
        segment_type: formType,
      }
    );

    if (result.error) {
      setCreateError(result.error.message);
      setCreating(false);
      return;
    }

    setFormName("");
    setFormDescription("");
    setFormType("manual");
    setDialogOpen(false);
    setCreating(false);
    fetchSegments();
  }

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading segments...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/stores" className="text-lg font-semibold hover:underline">
            Stores
          </Link>
          <span className="text-muted-foreground">/</span>
          <Link
            href={`/stores/${id}`}
            className="text-lg font-semibold hover:underline"
          >
            Store
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">Segments</h1>
        </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>Create Segment</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>New Customer Segment</DialogTitle>
              <DialogDescription>
                Define a customer group for targeted campaigns and analytics.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              {createError && (
                <p className="text-sm text-destructive">{createError}</p>
              )}
              <div className="space-y-2">
                <Label htmlFor="seg-name">Segment Name</Label>
                <Input
                  id="seg-name"
                  placeholder="e.g. VIP Customers"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="seg-desc">Description</Label>
                <Textarea
                  id="seg-desc"
                  placeholder="Customers who have spent over $500 lifetime..."
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  rows={3}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="seg-type">Type</Label>
                <Select
                  value={formType}
                  onValueChange={(v) =>
                    setFormType(v as "manual" | "dynamic")
                  }
                >
                  <SelectTrigger id="seg-type">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Manual</SelectItem>
                    <SelectItem value="dynamic">Dynamic</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={creating}>
                  {creating ? "Creating..." : "Create Segment"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </header>

      <main className="p-6">
        {error && (
          <Card className="mb-6 border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {segments.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="text-5xl opacity-20">&#9881;</div>
            <h2 className="text-xl font-semibold">No segments defined</h2>
            <p className="text-muted-foreground max-w-sm">
              Create your first customer segment to start grouping buyers
              for targeted marketing.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              Create your first segment
            </Button>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Customer Segments</CardTitle>
              <CardDescription>
                {segments.length} segment{segments.length !== 1 ? "s" : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Customers</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {segments.map((seg) => (
                    <TableRow key={seg.id}>
                      <TableCell>
                        <div>
                          <span className="font-medium">{seg.name}</span>
                          {seg.description && (
                            <p className="text-xs text-muted-foreground mt-0.5 max-w-xs truncate">
                              {seg.description}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            seg.segment_type === "dynamic" ? "default" : "secondary"
                          }
                        >
                          {seg.segment_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">
                        {seg.customer_count.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(seg.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
