"""Pydantic schemas for team member management endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/team/*`` routes.

**For Developers:**
    ``InviteTeamMemberRequest`` sends an email invite with a token.
    ``AcceptInviteRequest`` validates the token and links the user.
    ``TeamInviteResponse`` is used for invite-related responses (pending
    invitations). ``TeamMemberResponse`` is used for accepted team
    memberships. Both use ``from_attributes`` for ORM compatibility.

**For QA Engineers:**
    - ``InviteTeamMemberRequest.email`` must be a valid email.
    - ``InviteTeamMemberRequest.role`` should be ``"admin"``,
      ``"editor"``, or ``"viewer"``.
    - ``AcceptInviteRequest.token`` is a UUID-based invite token.
    - ``TeamInviteResponse.status`` is always ``"invited"`` for pending
      invitations.
    - ``TeamMemberResponse.status`` is ``"active"`` for accepted members.

**For Project Managers:**
    Team management enables collaborative store operation. The store
    owner invites team members via email with a specific role. Roles
    control access to different dashboard sections.

**For End Users:**
    Invite team members to help manage your store. Assign roles to
    control what each team member can see and do.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class InviteTeamMemberRequest(BaseModel):
    """Schema for inviting a new team member to a store.

    Attributes:
        email: Email address to send the invitation to.
        role: Permission role for the team member:
            ``"admin"`` (full access), ``"editor"`` (content management),
            or ``"viewer"`` (read-only).
    """

    email: EmailStr = Field(..., description="Invitee email address")
    role: str = Field(
        ..., description='Role: "admin", "editor", or "viewer"'
    )


class UpdateTeamMemberRequest(BaseModel):
    """Schema for updating a team member's role.

    Attributes:
        role: New permission role for the team member.
    """

    role: str = Field(
        ..., description='New role: "admin", "editor", or "viewer"'
    )


class TeamInviteResponse(BaseModel):
    """Schema for returning pending team invitation data in API responses.

    Maps from a ``TeamInvite`` ORM object. The ``status`` field is always
    ``"invited"`` to indicate the invitation has not yet been accepted.

    Attributes:
        id: The invite record's unique identifier.
        store_id: The store's UUID.
        email: Email address the invitation was sent to.
        role: Permission role assigned to the invitee.
        status: Always ``"invited"`` for pending invitations.
        created_at: When the invitation was created.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    email: str
    role: str
    status: str = "invited"
    created_at: datetime


class TeamMemberResponse(BaseModel):
    """Schema for returning accepted team member data in API responses.

    Maps from a ``TeamMember`` ORM object. The ``status`` field is always
    ``"active"`` for accepted members.

    Attributes:
        id: The team membership record's unique identifier.
        store_id: The store's UUID.
        user_id: The linked user's UUID.
        role: Permission role (``"admin"``, ``"editor"``, ``"viewer"``).
        email: Email address of the team member (from ``invited_email``
            on the ORM model, or the user's email if not set).
        status: Always ``"active"`` for accepted team members.
        created_at: When the team member was added.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    email: str | None = None
    status: str = "active"
    created_at: datetime


class PaginatedTeamMemberResponse(BaseModel):
    """Schema for paginated team member list responses.

    Items may include both pending invitations (``TeamInviteResponse``)
    and active members (``TeamMemberResponse``). Both share the same
    fields (``id``, ``store_id``, ``email``, ``role``, ``status``,
    ``created_at``).

    Attributes:
        items: List of team members / invites on this page.
        total: Total number of team members matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[TeamInviteResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AcceptInviteRequest(BaseModel):
    """Schema for accepting a team invitation.

    Attributes:
        token: The invite token received via email.
    """

    token: str = Field(..., description="Invite token from the email link")
