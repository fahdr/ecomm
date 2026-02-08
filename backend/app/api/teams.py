"""Teams API router.

Provides endpoints for managing store team members. Store owners can invite
team members, assign roles, and remove members. Invited users accept
invitations to join the team.

**For Developers:**
    Store-scoped routes are under ``/stores/{store_id}/team/...``.
    The invite acceptance route is under ``/team/accept-invite`` (no store scope).
    The ``get_current_user`` dependency is used for authentication.
    Service functions in ``team_service`` handle all business logic.
    The invite endpoint returns a ``TeamInviteResponse`` (pending invite).
    The update/remove/list endpoints work with both ``TeamInvite`` and
    ``TeamMember`` records transparently.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - POST invite returns 201 with the team invite data including
      ``status: "invited"``.
    - Roles: ``owner``, ``admin``, ``editor``, ``viewer``.
    - Cannot remove the store owner from the team.
    - Invite acceptance requires the invite token.
    - DELETE returns 204 with no content.
    - PATCH and DELETE accept both invite IDs and member IDs.

**For End Users:**
    - Invite team members to help manage your store.
    - Assign roles to control access levels.
    - Accept invitations to join a store's team.
    - Remove team members who no longer need access.
"""

import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.team import (
    AcceptInviteRequest,
    InviteTeamMemberRequest,
    PaginatedTeamMemberResponse,
    TeamInviteResponse,
    TeamMemberResponse,
    UpdateTeamMemberRequest,
)

router = APIRouter(tags=["teams"])


# ---------------------------------------------------------------------------
# Additional response schemas used only by the API layer
# ---------------------------------------------------------------------------


class AcceptInviteResponse(BaseModel):
    """Response after accepting a team invitation.

    Attributes:
        member: The activated team membership.
        message: Human-readable confirmation message.
    """

    member: TeamMemberResponse
    message: str


# ---------------------------------------------------------------------------
# Store-scoped route handlers
# ---------------------------------------------------------------------------


@router.post(
    "/stores/{store_id}/team/invite",
    response_model=TeamInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_team_member_endpoint(
    store_id: uuid.UUID,
    request: InviteTeamMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TeamInviteResponse:
    """Invite a new team member to a store.

    Sends an invitation email to the specified address. The invitee
    must accept the invitation to gain access. Only store owners
    and admins can invite new members.

    Args:
        store_id: The UUID of the store.
        request: Invite payload with email, role, and optional message.
        current_user: The authenticated store owner or admin.
        db: Async database session injected by FastAPI.

    Returns:
        TeamInviteResponse with the pending invitation data.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
        HTTPException 400: If the email is already a team member.
    """
    from app.services import team_service

    try:
        invite = await team_service.invite_member(
            db,
            store_id=store_id,
            user_id=current_user.id,
            email=request.email,
            role=request.role,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "already" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return TeamInviteResponse.model_validate(invite)


@router.get(
    "/stores/{store_id}/team",
    response_model=PaginatedTeamMemberResponse,
)
async def list_team_members_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedTeamMemberResponse:
    """List team members for a store with pagination.

    Returns all team members including pending invitations. Pending
    invitations are represented with ``status: "invited"`` and active
    members with ``status: "active"``.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated store owner or team member.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedTeamMemberResponse with members/invites and pagination
        metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import team_service

    try:
        all_items = await team_service.list_members_and_invites(
            db,
            store_id=store_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    total = len(all_items)
    pages = math.ceil(total / per_page) if total > 0 else 1
    offset = (page - 1) * per_page
    page_items = all_items[offset : offset + per_page]

    return PaginatedTeamMemberResponse(
        items=[TeamInviteResponse.model_validate(item) for item in page_items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.patch(
    "/stores/{store_id}/team/{member_id}",
    response_model=TeamInviteResponse,
)
async def update_team_member_role_endpoint(
    store_id: uuid.UUID,
    member_id: uuid.UUID,
    request: UpdateTeamMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TeamInviteResponse:
    """Update a team member's or pending invite's role.

    Only store owners and admins can change roles. Cannot change the
    store owner's role. Accepts both ``TeamMember`` and ``TeamInvite``
    IDs.

    Args:
        store_id: The UUID of the store.
        member_id: The UUID of the team membership or invite to update.
        request: Role update payload.
        current_user: The authenticated store owner or admin.
        db: Async database session injected by FastAPI.

    Returns:
        TeamInviteResponse with the updated data.

    Raises:
        HTTPException 404: If the store or member/invite is not found.
        HTTPException 400: If trying to change the owner's role.
    """
    from app.services import team_service

    try:
        record = await team_service.update_member_or_invite_role(
            db,
            store_id=store_id,
            user_id=current_user.id,
            member_id=member_id,
            role=request.role,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "owner" in detail.lower() or "cannot" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return TeamInviteResponse.model_validate(record)


@router.delete(
    "/stores/{store_id}/team/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_team_member_endpoint(
    store_id: uuid.UUID,
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a team member or pending invite from a store.

    Cannot remove the store owner. Only store owners and admins
    can remove members. Accepts both ``TeamMember`` and ``TeamInvite``
    IDs.

    Args:
        store_id: The UUID of the store.
        member_id: The UUID of the team membership or invite to remove.
        current_user: The authenticated store owner or admin.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the store or member/invite is not found.
        HTTPException 400: If trying to remove the store owner.
    """
    from app.services import team_service

    try:
        await team_service.remove_member_or_invite(
            db,
            store_id=store_id,
            user_id=current_user.id,
            member_id=member_id,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "owner" in detail.lower() or "cannot" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Non-store-scoped route handlers
# ---------------------------------------------------------------------------


@router.post("/team/accept-invite", response_model=AcceptInviteResponse)
async def accept_invite_endpoint(
    request: AcceptInviteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AcceptInviteResponse:
    """Accept a team invitation.

    The authenticated user accepts an invitation using the token
    received in the invitation email. The user's account is linked
    to the team membership and gains access to the store.

    Args:
        request: Accept invite payload with the invitation token.
        current_user: The authenticated user accepting the invite.
        db: Async database session injected by FastAPI.

    Returns:
        AcceptInviteResponse with the activated membership and confirmation.

    Raises:
        HTTPException 400: If the token is invalid, expired, or already used.
        HTTPException 404: If the invitation is not found.
    """
    from app.services import team_service

    try:
        member = await team_service.accept_invite(
            db,
            user_id=current_user.id,
            token=request.token,
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "invalid" in detail.lower()
            or "expired" in detail.lower()
            or "already" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return AcceptInviteResponse(
        member=TeamMemberResponse.model_validate(member),
        message="Invitation accepted successfully",
    )
