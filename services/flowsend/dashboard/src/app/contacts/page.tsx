/**
 * Contacts page — manage subscribers, import contacts, and organize with tags.
 *
 * Displays a searchable, paginated table of contacts with tag badges,
 * subscription status, and actions (edit, delete). Includes a create
 * contact dialog, bulk import dialog, and contact list management.
 *
 * **For Developers:**
 *   - `GET /api/v1/contacts?page=&page_size=&search=&tag=` — paginated contacts list.
 *   - `POST /api/v1/contacts` — create a single contact.
 *   - `PATCH /api/v1/contacts/:id` — update a contact.
 *   - `DELETE /api/v1/contacts/:id` — delete a contact (204 No Content).
 *   - `POST /api/v1/contacts/import` — bulk import from email list or CSV.
 *   - `GET /api/v1/contacts/count` — total contact count for KPI display.
 *   - All API responses follow the `{ data, error }` envelope from `api.ts`.
 *
 * **For Project Managers:**
 *   - Contacts are the foundation of email marketing — every campaign and
 *     flow targets contacts. This page must be fast and easy to navigate.
 *   - The import feature reduces onboarding friction for new users migrating
 *     from another platform.
 *
 * **For QA Engineers:**
 *   - Test with 0, 1, and many contacts to verify empty state, single row, and pagination.
 *   - Verify search filters by email and name substring.
 *   - Test tag filter dropdown updates the table correctly.
 *   - Verify the create dialog validates email format (422 on invalid).
 *   - Test bulk import with duplicate emails (should report skipped count).
 *   - Verify delete confirmation dialog prevents accidental deletion.
 *   - Check that unsubscribed contacts display a distinct visual indicator.
 *
 * **For End Users:**
 *   - View and manage all your email subscribers in one place.
 *   - Use the search bar to find contacts by email or name.
 *   - Import contacts in bulk using a comma-separated email list.
 *   - Click a contact row to edit tags, name, or subscription status.
 */

"use client";

import * as React from "react";
import {
  Users,
  Plus,
  Search,
  Upload,
  Trash2,
  Pencil,
  Loader2,
  Mail,
  UserCheck,
  UserX,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Shell } from "@/components/shell";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
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
import {
  FadeIn,
  StaggerChildren,
  AnimatedCounter,
  PageTransition,
} from "@/components/motion";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Shape of a contact as returned by the API. */
interface Contact {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  tags: string[];
  is_subscribed: boolean;
  created_at: string;
  updated_at: string;
}

/** Shape of a paginated API response. */
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/** Shape of the contact import response. */
interface ImportResult {
  imported: number;
  skipped: number;
  total: number;
}

/**
 * Contacts page component.
 *
 * @returns The contacts management page wrapped in the Shell layout.
 */
export default function ContactsPage() {
  /* ── List state ── */
  const [contacts, setContacts] = React.useState<Contact[]>([]);
  const [totalContacts, setTotalContacts] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [pageSize] = React.useState(20);
  const [search, setSearch] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* ── Contact count for KPI ── */
  const [contactCount, setContactCount] = React.useState(0);

  /* ── Create dialog state ── */
  const [createOpen, setCreateOpen] = React.useState(false);
  const [newEmail, setNewEmail] = React.useState("");
  const [newFirstName, setNewFirstName] = React.useState("");
  const [newLastName, setNewLastName] = React.useState("");
  const [newTags, setNewTags] = React.useState("");
  const [creating, setCreating] = React.useState(false);

  /* ── Edit dialog state ── */
  const [editTarget, setEditTarget] = React.useState<Contact | null>(null);
  const [editEmail, setEditEmail] = React.useState("");
  const [editFirstName, setEditFirstName] = React.useState("");
  const [editLastName, setEditLastName] = React.useState("");
  const [editTags, setEditTags] = React.useState("");
  const [editSubscribed, setEditSubscribed] = React.useState(true);
  const [saving, setSaving] = React.useState(false);

  /* ── Import dialog state ── */
  const [importOpen, setImportOpen] = React.useState(false);
  const [importEmails, setImportEmails] = React.useState("");
  const [importTags, setImportTags] = React.useState("");
  const [importing, setImporting] = React.useState(false);
  const [importResult, setImportResult] = React.useState<ImportResult | null>(
    null
  );

  /* ── Delete dialog state ── */
  const [deleteTarget, setDeleteTarget] = React.useState<Contact | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  /** Debounce timer for search input. */
  const searchTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(
    null
  );

  /**
   * Fetch contacts from the API with current pagination and search params.
   */
  async function fetchContacts() {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (search.trim()) params.set("search", search.trim());

    const { data, error: apiError } = await api.get<PaginatedResponse<Contact>>(
      `/api/v1/contacts?${params.toString()}`
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setContacts(data.items);
      setTotalContacts(data.total);
    }
    setLoading(false);
  }

  /**
   * Fetch the total contact count for the KPI card.
   */
  async function fetchContactCount() {
    const { data } = await api.get<{ count: number }>("/api/v1/contacts/count");
    if (data) setContactCount(data.count);
  }

  /** Fetch on mount and when page/search changes. */
  React.useEffect(() => {
    fetchContacts();
    fetchContactCount();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  /**
   * Handle search input with debounce (300ms).
   *
   * @param value - The search string typed by the user.
   */
  function handleSearchChange(value: string) {
    setSearch(value);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setPage(1);
      fetchContacts();
    }, 300);
  }

  /**
   * Create a new contact via the API.
   * Closes the dialog and refreshes the list on success.
   */
  async function handleCreateContact() {
    if (!newEmail.trim()) {
      setError("Email is required.");
      return;
    }
    setCreating(true);
    setError(null);

    const tags = newTags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    const { error: apiError } = await api.post("/api/v1/contacts", {
      email: newEmail.trim(),
      first_name: newFirstName.trim() || null,
      last_name: newLastName.trim() || null,
      tags,
    });
    setCreating(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setCreateOpen(false);
    setNewEmail("");
    setNewFirstName("");
    setNewLastName("");
    setNewTags("");
    fetchContacts();
    fetchContactCount();
  }

  /**
   * Open the edit dialog pre-filled with the selected contact's data.
   *
   * @param contact - The contact to edit.
   */
  function openEditDialog(contact: Contact) {
    setEditTarget(contact);
    setEditEmail(contact.email);
    setEditFirstName(contact.first_name || "");
    setEditLastName(contact.last_name || "");
    setEditTags(contact.tags.join(", "));
    setEditSubscribed(contact.is_subscribed);
  }

  /**
   * Save edits to the selected contact via PATCH.
   */
  async function handleSaveEdit() {
    if (!editTarget) return;
    setSaving(true);
    setError(null);

    const tags = editTags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    const { error: apiError } = await api.patch(
      `/api/v1/contacts/${editTarget.id}`,
      {
        email: editEmail.trim() || undefined,
        first_name: editFirstName.trim() || null,
        last_name: editLastName.trim() || null,
        tags,
        is_subscribed: editSubscribed,
      }
    );
    setSaving(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setEditTarget(null);
    fetchContacts();
  }

  /**
   * Bulk import contacts from a comma-separated email list.
   */
  async function handleImport() {
    const emails = importEmails
      .split(/[\n,;]+/)
      .map((e) => e.trim())
      .filter(Boolean);

    if (emails.length === 0) {
      setError("Please enter at least one email address.");
      return;
    }

    setImporting(true);
    setError(null);
    setImportResult(null);

    const tags = importTags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    const { data, error: apiError } = await api.post<ImportResult>(
      "/api/v1/contacts/import",
      { emails, tags }
    );
    setImporting(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    if (data) {
      setImportResult(data);
      fetchContacts();
      fetchContactCount();
    }
  }

  /**
   * Delete a contact after confirmation.
   *
   * @param id - The contact UUID to delete.
   */
  async function handleDelete(id: string) {
    setDeleting(true);
    const { error: apiError } = await api.del(`/api/v1/contacts/${id}`);
    setDeleting(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setDeleteTarget(null);
    fetchContacts();
    fetchContactCount();
  }

  /** Total number of pages based on total contacts and page size. */
  const totalPages = Math.max(1, Math.ceil(totalContacts / pageSize));

  /**
   * Format an ISO date string for display.
   *
   * @param dateStr - ISO date string.
   * @returns A formatted date string.
   */
  function formatDate(dateStr: string): string {
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
                Contacts
              </h2>
              <p className="text-muted-foreground mt-1">
                Manage your email subscribers and contact lists.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => setImportOpen(true)}>
                <Upload className="size-4" />
                Import
              </Button>
              <Button onClick={() => setCreateOpen(true)}>
                <Plus className="size-4" />
                Add Contact
              </Button>
            </div>
          </div>
        </FadeIn>

        {/* ── KPI Summary Cards ── */}
        <StaggerChildren
          className="grid grid-cols-1 md:grid-cols-3 gap-4"
          staggerDelay={0.08}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Contacts
              </CardTitle>
              <Users className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <AnimatedCounter
                value={contactCount}
                formatter={(v) => v.toLocaleString()}
                className="text-3xl font-bold font-heading"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Subscribed
              </CardTitle>
              <UserCheck className="size-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <AnimatedCounter
                value={contacts.filter((c) => c.is_subscribed).length}
                className="text-3xl font-bold font-heading text-emerald-600 dark:text-emerald-400"
              />
              <p className="text-xs text-muted-foreground mt-1">
                on current page
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Unsubscribed
              </CardTitle>
              <UserX className="size-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <AnimatedCounter
                value={contacts.filter((c) => !c.is_subscribed).length}
                className="text-3xl font-bold font-heading text-red-600 dark:text-red-400"
              />
              <p className="text-xs text-muted-foreground mt-1">
                on current page
              </p>
            </CardContent>
          </Card>
        </StaggerChildren>

        {/* ── Search Bar ── */}
        <FadeIn delay={0.15}>
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Search by email or name..."
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-9"
            />
          </div>
        </FadeIn>

        {/* ── Contact Table ── */}
        {loading ? (
          <Card>
            <CardContent className="pt-6 space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="size-9 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-3 w-60" />
                  </div>
                  <Skeleton className="h-8 w-16" />
                </div>
              ))}
            </CardContent>
          </Card>
        ) : contacts.length === 0 ? (
          <FadeIn>
            <Card>
              <CardContent className="pt-12 pb-12 text-center">
                <div className="mx-auto size-12 rounded-full bg-muted flex items-center justify-center mb-4">
                  <Users className="size-6 text-muted-foreground" />
                </div>
                <h3 className="font-heading font-semibold text-lg">
                  {search ? "No contacts found" : "No contacts yet"}
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                  {search
                    ? "Try adjusting your search query."
                    : "Add your first contact or import subscribers in bulk to get started."}
                </p>
                {!search && (
                  <div className="flex items-center justify-center gap-2 mt-4">
                    <Button onClick={() => setCreateOpen(true)}>
                      <Plus className="size-4" />
                      Add Contact
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setImportOpen(true)}
                    >
                      <Upload className="size-4" />
                      Import
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <FadeIn delay={0.2}>
            <Card>
              <CardContent className="pt-4">
                {/* Table header */}
                <div className="grid grid-cols-[1fr_1fr_auto_auto_auto] gap-4 px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider border-b">
                  <span>Email</span>
                  <span>Name</span>
                  <span>Tags</span>
                  <span>Status</span>
                  <span className="text-right">Actions</span>
                </div>

                {/* Table rows */}
                <div className="divide-y">
                  {contacts.map((contact) => (
                    <div
                      key={contact.id}
                      className="grid grid-cols-[1fr_1fr_auto_auto_auto] gap-4 px-4 py-3 items-center hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="size-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                          <Mail className="size-4 text-primary" />
                        </div>
                        <span className="text-sm truncate">
                          {contact.email}
                        </span>
                      </div>

                      <span className="text-sm text-muted-foreground truncate">
                        {[contact.first_name, contact.last_name]
                          .filter(Boolean)
                          .join(" ") || "--"}
                      </span>

                      <div className="flex items-center gap-1 flex-wrap max-w-[200px]">
                        {contact.tags.length > 0 ? (
                          contact.tags.slice(0, 3).map((tag) => (
                            <Badge
                              key={tag}
                              variant="secondary"
                              className="text-xs"
                            >
                              {tag}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            --
                          </span>
                        )}
                        {contact.tags.length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{contact.tags.length - 3}
                          </Badge>
                        )}
                      </div>

                      <Badge
                        variant={
                          contact.is_subscribed ? "success" : "destructive"
                        }
                      >
                        {contact.is_subscribed ? "Subscribed" : "Unsubscribed"}
                      </Badge>

                      <div className="flex items-center gap-1 justify-end">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          onClick={() => openEditDialog(contact)}
                        >
                          <Pencil className="size-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-muted-foreground hover:text-destructive"
                          onClick={() => setDeleteTarget(contact)}
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination controls */}
                <div className="flex items-center justify-between px-4 py-3 border-t">
                  <p className="text-sm text-muted-foreground">
                    Showing {(page - 1) * pageSize + 1}
                    {" - "}
                    {Math.min(page * pageSize, totalContacts)} of{" "}
                    {totalContacts.toLocaleString()} contacts
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                    >
                      <ChevronLeft className="size-4" />
                      Previous
                    </Button>
                    <span className="text-sm text-muted-foreground px-2">
                      Page {page} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                      <ChevronRight className="size-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* ── Error Message ── */}
        {error && (
          <FadeIn>
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </FadeIn>
        )}

        {/* ── Create Contact Dialog ── */}
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Contact</DialogTitle>
              <DialogDescription>
                Add a new subscriber to your contact list.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label htmlFor="contact-email" className="text-sm font-medium">
                  Email *
                </label>
                <Input
                  id="contact-email"
                  type="email"
                  placeholder="subscriber@example.com"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label
                    htmlFor="contact-first"
                    className="text-sm font-medium"
                  >
                    First Name
                  </label>
                  <Input
                    id="contact-first"
                    placeholder="Alice"
                    value={newFirstName}
                    onChange={(e) => setNewFirstName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label
                    htmlFor="contact-last"
                    className="text-sm font-medium"
                  >
                    Last Name
                  </label>
                  <Input
                    id="contact-last"
                    placeholder="Smith"
                    value={newLastName}
                    onChange={(e) => setNewLastName(e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label htmlFor="contact-tags" className="text-sm font-medium">
                  Tags
                </label>
                <Input
                  id="contact-tags"
                  placeholder="vip, newsletter, beta"
                  value={newTags}
                  onChange={(e) => setNewTags(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated list of tags for segmentation.
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
              <Button onClick={handleCreateContact} disabled={creating}>
                {creating && <Loader2 className="size-4 animate-spin" />}
                {creating ? "Adding..." : "Add Contact"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Edit Contact Dialog ── */}
        <Dialog
          open={editTarget !== null}
          onOpenChange={(open) => {
            if (!open) setEditTarget(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Contact</DialogTitle>
              <DialogDescription>
                Update contact details and subscription status.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label htmlFor="edit-email" className="text-sm font-medium">
                  Email
                </label>
                <Input
                  id="edit-email"
                  type="email"
                  value={editEmail}
                  onChange={(e) => setEditEmail(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label
                    htmlFor="edit-first"
                    className="text-sm font-medium"
                  >
                    First Name
                  </label>
                  <Input
                    id="edit-first"
                    value={editFirstName}
                    onChange={(e) => setEditFirstName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="edit-last" className="text-sm font-medium">
                    Last Name
                  </label>
                  <Input
                    id="edit-last"
                    value={editLastName}
                    onChange={(e) => setEditLastName(e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label htmlFor="edit-tags" className="text-sm font-medium">
                  Tags
                </label>
                <Input
                  id="edit-tags"
                  value={editTags}
                  onChange={(e) => setEditTags(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-3">
                <label htmlFor="edit-subscribed" className="text-sm font-medium">
                  Subscribed
                </label>
                <button
                  id="edit-subscribed"
                  type="button"
                  role="switch"
                  aria-checked={editSubscribed}
                  onClick={() => setEditSubscribed(!editSubscribed)}
                  className={cn(
                    "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                    editSubscribed ? "bg-emerald-500" : "bg-muted"
                  )}
                >
                  <span
                    className={cn(
                      "inline-block size-4 rounded-full bg-white transition-transform",
                      editSubscribed ? "translate-x-6" : "translate-x-1"
                    )}
                  />
                </button>
                <span className="text-sm text-muted-foreground">
                  {editSubscribed ? "Active" : "Unsubscribed"}
                </span>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setEditTarget(null)}
                disabled={saving}
              >
                Cancel
              </Button>
              <Button onClick={handleSaveEdit} disabled={saving}>
                {saving && <Loader2 className="size-4 animate-spin" />}
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Import Dialog ── */}
        <Dialog open={importOpen} onOpenChange={setImportOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Import Contacts</DialogTitle>
              <DialogDescription>
                Paste email addresses separated by commas, semicolons, or
                newlines. Duplicate emails will be skipped automatically.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label htmlFor="import-emails" className="text-sm font-medium">
                  Email Addresses *
                </label>
                <textarea
                  id="import-emails"
                  rows={6}
                  placeholder={"alice@example.com\nbob@example.com\ncharlie@example.com"}
                  value={importEmails}
                  onChange={(e) => setImportEmails(e.target.value)}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="import-tags" className="text-sm font-medium">
                  Tags (optional)
                </label>
                <Input
                  id="import-tags"
                  placeholder="imported, newsletter"
                  value={importTags}
                  onChange={(e) => setImportTags(e.target.value)}
                />
              </div>
              {importResult && (
                <div className="rounded-md bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 p-3">
                  <p className="text-sm font-medium text-emerald-800 dark:text-emerald-300">
                    Import complete
                  </p>
                  <p className="text-sm text-emerald-700 dark:text-emerald-400 mt-1">
                    {importResult.imported} imported, {importResult.skipped}{" "}
                    skipped, {importResult.total} total processed.
                  </p>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setImportOpen(false);
                  setImportResult(null);
                  setImportEmails("");
                  setImportTags("");
                }}
                disabled={importing}
              >
                {importResult ? "Done" : "Cancel"}
              </Button>
              {!importResult && (
                <Button onClick={handleImport} disabled={importing}>
                  {importing && <Loader2 className="size-4 animate-spin" />}
                  {importing ? "Importing..." : "Import Contacts"}
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Delete Confirmation Dialog ── */}
        <Dialog
          open={deleteTarget !== null}
          onOpenChange={(open) => {
            if (!open) setDeleteTarget(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Contact</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete{" "}
                <strong>{deleteTarget?.email}</strong>? This action cannot be
                undone. The contact will be removed from all lists and flows.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() =>
                  deleteTarget && handleDelete(deleteTarget.id)
                }
                disabled={deleting}
              >
                {deleting && <Loader2 className="size-4 animate-spin" />}
                {deleting ? "Deleting..." : "Delete Contact"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
