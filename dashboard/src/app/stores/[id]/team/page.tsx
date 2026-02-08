/**
 * Team management page.
 *
 * Lists all team members associated with a store and provides a dialog
 * to invite new members by email with a specific role assignment.
 *
 * **For End Users:**
 *   Manage who has access to your store. Invite team members and assign
 *   roles like Admin, Editor, or Viewer to control their permissions.
 *
 * **For Developers:**
 *   - Fetches team members via `GET /api/v1/stores/{store_id}/team`.
 *   - Invites new members via `POST /api/v1/stores/{store_id}/team`.
 *   - Role values: "admin", "editor", "viewer".
 *
 * **For QA Engineers:**
 *   - Verify that the team list refreshes after inviting a new member.
 *   - Verify that duplicate email invitations show an error message.
 *   - Verify that role selection defaults to "viewer".
 *   - Verify that pending invitations display the "invited" status badge.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 24 (Teams) in the backlog.
 *   Team members are store-scoped with role-based access control.
 */

"use client";

import { FormEvent, useEffect, useState, use } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

/** Shape of a team member returned by the API. */
interface TeamMember {
  id: string;
  email: string;
  role: "owner" | "admin" | "editor" | "viewer";
  status: "active" | "invited" | "deactivated";
  joined_at: string | null;
  invited_at: string;
}

/**
 * TeamPage renders the team member listing and invitation dialog.
 *
 * @param params - Route parameters containing the store ID.
 * @returns The rendered team management page.
 */
export default function TeamPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user, loading: authLoading } = useAuth();
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Invite form state */
  const [dialogOpen, setDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);

  /**
   * Fetch all team members for this store.
   */
  async function fetchMembers() {
    setLoading(true);
    const result = await api.get<{ items: TeamMember[] }>(`/api/v1/stores/${id}/team`);
    if (result.error) {
      setError(result.error.message);
    } else {
      setMembers(result.data?.items ?? []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchMembers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, user, authLoading]);

  /**
   * Handle the invite-member form submission.
   *
   * @param e - The form submission event.
   */
  async function handleInvite(e: FormEvent) {
    e.preventDefault();
    setInviting(true);
    setInviteError(null);

    const result = await api.post<TeamMember>(`/api/v1/stores/${id}/team/invite`, {
      email: inviteEmail,
      role: inviteRole,
    });

    if (result.error) {
      setInviteError(result.error.message);
      setInviting(false);
      return;
    }

    setInviteEmail("");
    setInviteRole("viewer");
    setDialogOpen(false);
    setInviting(false);
    fetchMembers();
  }

  /**
   * Map member status to a Badge variant.
   *
   * @param status - The team member status.
   * @returns The appropriate Badge variant.
   */
  function statusVariant(
    status: TeamMember["status"]
  ): "default" | "secondary" | "outline" {
    switch (status) {
      case "active":
        return "default";
      case "invited":
        return "secondary";
      case "deactivated":
        return "outline";
      default:
        return "outline";
    }
  }

  /**
   * Map member role to a Badge variant for visual distinction.
   *
   * @param role - The team member role.
   * @returns The appropriate Badge variant.
   */
  function roleVariant(
    role: TeamMember["role"]
  ): "default" | "secondary" | "outline" {
    switch (role) {
      case "owner":
        return "default";
      case "admin":
        return "default";
      case "editor":
        return "secondary";
      case "viewer":
        return "outline";
      default:
        return "outline";
    }
  }

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading team...</p>
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
          <h1 className="text-lg font-semibold">Team</h1>
        </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>Invite Member</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Invite Team Member</DialogTitle>
              <DialogDescription>
                Send an invitation email with the selected role. The invitee
                will need to accept before gaining access.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleInvite} className="space-y-4">
              {inviteError && (
                <p className="text-sm text-destructive">{inviteError}</p>
              )}
              <div className="space-y-2">
                <Label htmlFor="invite-email">Email Address</Label>
                <Input
                  id="invite-email"
                  type="email"
                  placeholder="colleague@example.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-role">Role</Label>
                <Select value={inviteRole} onValueChange={setInviteRole}>
                  <SelectTrigger id="invite-role">
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="editor">Editor</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
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
                <Button type="submit" disabled={inviting}>
                  {inviting ? "Inviting..." : "Send Invitation"}
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

        {members.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="text-5xl opacity-20">&#128101;</div>
            <h2 className="text-xl font-semibold">No team members yet</h2>
            <p className="text-muted-foreground max-w-sm">
              Invite your first team member to collaborate on managing
              your store.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              Invite your first member
            </Button>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Team Members</CardTitle>
              <CardDescription>
                {members.length} member{members.length !== 1 ? "s" : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Joined</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {members.map((member) => (
                    <TableRow key={member.id}>
                      <TableCell className="font-medium">
                        {member.email}
                      </TableCell>
                      <TableCell>
                        <Badge variant={roleVariant(member.role)}>
                          {member.role}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(member.status)}>
                          {member.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {member.joined_at
                          ? new Date(member.joined_at).toLocaleDateString()
                          : "Pending"}
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
