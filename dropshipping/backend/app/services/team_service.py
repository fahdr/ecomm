"""Team business logic.

Handles multi-user store access via team invitations and memberships.
Store owners can invite other users by email, assign roles, and manage
team member access.

**For Developers:**
    Invitations use a unique token for accepting. The ``TeamMember``
    record represents a confirmed membership with a role. The
    ``TeamInvite`` record represents a pending invitation. Update and
    remove operations transparently handle both record types.
    The ``check_store_access`` function is intended for use in API
    dependencies to verify team-based access beyond direct ownership.

**For QA Engineers:**
    - ``invite_member`` checks that the invitee is not already a member
      and that the email is not the store owner's.
    - ``accept_invite`` validates the token and creates a TeamMember.
    - ``remove_member_or_invite`` prevents the store owner from being
      removed and works with both invite and member IDs.
    - ``update_member_or_invite_role`` prevents changing the owner's
      role and works with both invite and member IDs.
    - ``list_members_and_invites`` returns both accepted members and
      pending invitations.
    - ``check_store_access`` returns the role string or None.
    - ``get_user_stores_via_teams`` returns stores a user can access
      through team membership (not ownership).

**For Project Managers:**
    This service powers Feature 24 (Teams & Roles) from the backlog.
    It enables store owners to delegate store management to team members
    with role-based permissions.

**For End Users:**
    Invite team members to help manage your store. Assign roles like
    "admin", "editor", or "viewer" to control what each member can do.
    Team members accept invitations via a unique link.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store, StoreStatus


# ---------------------------------------------------------------------------
# Team models -- import conditionally.
# ---------------------------------------------------------------------------
try:
    from app.models.team import TeamInvite, TeamMember
except ImportError:
    TeamInvite = None  # type: ignore[assignment,misc]
    TeamMember = None  # type: ignore[assignment,misc]


async def _verify_store_ownership(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> Store:
    """Verify that a store exists and belongs to the given user.

    Args:
        db: Async database session.
        store_id: The UUID of the store.
        user_id: The requesting user's UUID.

    Returns:
        The Store ORM instance.

    Raises:
        ValueError: If the store doesn't exist, is deleted, or belongs
            to a different user.
    """
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted:
        raise ValueError("Store not found")
    if store.user_id != user_id:
        raise ValueError("Store not found")
    return store


async def invite_member(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    email: str,
    role: str = "editor",
) -> "TeamInvite":
    """Invite a user to join a store's team.

    Generates a unique invite token and creates a pending invitation.
    Validates that the invitee is not already a member and the email
    is not the store owner's.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (must be store owner).
        email: Email address of the person to invite.
        role: The role to assign (e.g. ``"admin"``, ``"editor"``,
            ``"viewer"``). Defaults to ``"editor"``.

    Returns:
        The newly created TeamInvite ORM instance.

    Raises:
        ValueError: If the store doesn't exist, belongs to another user,
            the invitee is the store owner, or the email is already a
            team member.
    """
    store = await _verify_store_ownership(db, store_id, user_id)

    # Prevent inviting yourself (the store owner)
    from app.models.user import User
    owner_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    owner = owner_result.scalar_one_or_none()
    if owner and owner.email == email:
        raise ValueError("Cannot invite yourself to your own store")

    # Check if already a member
    existing_member = await db.execute(
        select(TeamMember)
        .join(User, TeamMember.user_id == User.id)
        .where(
            TeamMember.store_id == store_id,
            User.email == email,
        )
    )
    if existing_member.scalar_one_or_none() is not None:
        raise ValueError("This user is already a team member")

    # Check for pending (non-expired) invite
    now = datetime.now(timezone.utc)
    existing_invite = await db.execute(
        select(TeamInvite).where(
            TeamInvite.store_id == store_id,
            TeamInvite.email == email,
            TeamInvite.expires_at > now,
        )
    )
    if existing_invite.scalar_one_or_none() is not None:
        raise ValueError("An invitation has already been sent to this email")

    # Generate unique token
    token = secrets.token_urlsafe(32)

    invite = TeamInvite(
        store_id=store_id,
        email=email,
        role=role,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    await db.flush()
    await db.refresh(invite)
    return invite


async def list_members(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list:
    """List all accepted team members for a store.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        A list of TeamMember ORM instances.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(TeamMember)
        .where(TeamMember.store_id == store_id)
        .order_by(TeamMember.created_at)
    )
    return list(result.scalars().all())


async def list_members_and_invites(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list:
    """List all team members and pending invites for a store.

    Returns both accepted ``TeamMember`` records and pending
    ``TeamInvite`` records. Each invite is augmented with a transient
    ``status`` attribute set to ``"invited"`` so that the API layer
    can serialize them uniformly via ``TeamInviteResponse``.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        A combined list of TeamMember and TeamInvite ORM instances,
        ordered by creation time.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)

    # Fetch accepted members
    members_result = await db.execute(
        select(TeamMember)
        .where(TeamMember.store_id == store_id)
        .order_by(TeamMember.created_at)
    )
    members = list(members_result.scalars().all())

    # Fetch pending invites (non-expired)
    now = datetime.now(timezone.utc)
    invites_result = await db.execute(
        select(TeamInvite)
        .where(
            TeamInvite.store_id == store_id,
            TeamInvite.expires_at > now,
        )
        .order_by(TeamInvite.created_at)
    )
    invites = list(invites_result.scalars().all())

    # Combine and return; invites already have ``email`` attribute,
    # and ``TeamInviteResponse.status`` defaults to ``"invited"``.
    # For members, set ``email`` from ``invited_email`` so that the
    # response schema can serialize them.
    for m in members:
        m.email = m.invited_email  # type: ignore[attr-defined]
        m.status = "active"  # type: ignore[attr-defined]
    for inv in invites:
        inv.status = "invited"  # type: ignore[attr-defined]

    return members + invites


async def update_member_role(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    member_id: uuid.UUID,
    role: str,
) -> "TeamMember":
    """Update a team member's role.

    Prevents changing the store owner's role through the team system.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (must be store owner).
        member_id: The UUID of the TeamMember record to update.
        role: The new role string (e.g. ``"admin"``, ``"editor"``,
            ``"viewer"``).

    Returns:
        The updated TeamMember ORM instance.

    Raises:
        ValueError: If the store or member doesn't exist, the store
            belongs to another user, or attempting to change the owner's
            role.
    """
    store = await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(TeamMember).where(
            TeamMember.id == member_id,
            TeamMember.store_id == store_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise ValueError("Team member not found")

    # Prevent changing the store owner's role
    if member.user_id == store.user_id:
        raise ValueError("Cannot change the store owner's role")

    member.role = role
    await db.flush()
    await db.refresh(member)
    return member


async def update_member_or_invite_role(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    member_id: uuid.UUID,
    role: str,
) -> "TeamMember | TeamInvite":
    """Update a team member's or pending invite's role.

    First looks for a ``TeamMember`` record, then falls back to
    ``TeamInvite``. Prevents changing the store owner's role.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (must be store owner).
        member_id: The UUID of the TeamMember or TeamInvite record.
        role: The new role string.

    Returns:
        The updated TeamMember or TeamInvite ORM instance.

    Raises:
        ValueError: If neither a member nor invite is found, the store
            belongs to another user, or attempting to change the owner's
            role.
    """
    store = await _verify_store_ownership(db, store_id, user_id)

    # Try TeamMember first
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.id == member_id,
            TeamMember.store_id == store_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is not None:
        if member.user_id == store.user_id:
            raise ValueError("Cannot change the store owner's role")
        member.role = role
        await db.flush()
        await db.refresh(member)
        # Set transient email for response serialization
        member.email = member.invited_email  # type: ignore[attr-defined]
        member.status = "active"  # type: ignore[attr-defined]
        return member

    # Try TeamInvite
    invite_result = await db.execute(
        select(TeamInvite).where(
            TeamInvite.id == member_id,
            TeamInvite.store_id == store_id,
        )
    )
    invite = invite_result.scalar_one_or_none()
    if invite is not None:
        invite.role = role
        await db.flush()
        await db.refresh(invite)
        return invite

    raise ValueError("Team member not found")


async def remove_member(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    member_id: uuid.UUID,
) -> None:
    """Remove a team member from a store.

    Prevents removing the store owner from the team.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (must be store owner).
        member_id: The UUID of the TeamMember record to remove.

    Raises:
        ValueError: If the store or member doesn't exist, the store
            belongs to another user, or attempting to remove the owner.
    """
    store = await _verify_store_ownership(db, store_id, user_id)

    result = await db.execute(
        select(TeamMember).where(
            TeamMember.id == member_id,
            TeamMember.store_id == store_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise ValueError("Team member not found")

    if member.user_id == store.user_id:
        raise ValueError("Cannot remove the store owner from the team")

    await db.delete(member)
    await db.flush()


async def remove_member_or_invite(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    member_id: uuid.UUID,
) -> None:
    """Remove a team member or pending invite from a store.

    First looks for a ``TeamMember`` record, then falls back to
    ``TeamInvite``. Prevents removing the store owner.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (must be store owner).
        member_id: The UUID of the TeamMember or TeamInvite to remove.

    Raises:
        ValueError: If neither a member nor invite is found, the store
            belongs to another user, or attempting to remove the owner.
    """
    store = await _verify_store_ownership(db, store_id, user_id)

    # Try TeamMember first
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.id == member_id,
            TeamMember.store_id == store_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is not None:
        if member.user_id == store.user_id:
            raise ValueError("Cannot remove the store owner from the team")
        await db.delete(member)
        await db.flush()
        return

    # Try TeamInvite
    invite_result = await db.execute(
        select(TeamInvite).where(
            TeamInvite.id == member_id,
            TeamInvite.store_id == store_id,
        )
    )
    invite = invite_result.scalar_one_or_none()
    if invite is not None:
        await db.delete(invite)
        await db.flush()
        return

    raise ValueError("Team member not found")


async def accept_invite(
    db: AsyncSession,
    token: str,
    user_id: uuid.UUID,
) -> "TeamMember":
    """Accept a team invitation using its unique token.

    Validates the token, checks it hasn't expired or been used, and
    creates a TeamMember record for the accepting user.

    Args:
        db: Async database session.
        token: The invitation token string.
        user_id: The UUID of the user accepting the invitation.

    Returns:
        The newly created TeamMember ORM instance.

    Raises:
        ValueError: If the token is invalid, expired, already used, or
            the user is already a team member.
    """
    result = await db.execute(
        select(TeamInvite).where(TeamInvite.token == token)
    )
    invite = result.scalar_one_or_none()
    if invite is None:
        raise ValueError("Invalid invitation token")

    now = datetime.now(timezone.utc)
    if invite.expires_at and now > invite.expires_at:
        await db.delete(invite)
        await db.flush()
        raise ValueError("This invitation has expired")

    # Check if user is already a member
    existing = await db.execute(
        select(TeamMember).where(
            TeamMember.store_id == invite.store_id,
            TeamMember.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("You are already a member of this store's team")

    # Create membership
    member = TeamMember(
        store_id=invite.store_id,
        user_id=user_id,
        role=invite.role,
        invited_email=invite.email,
        invite_accepted=True,
    )
    db.add(member)

    # Remove the invite now that it has been accepted
    await db.delete(invite)

    await db.flush()
    await db.refresh(member)
    return member


async def get_user_stores_via_teams(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list:
    """Get stores a user has access to via team membership.

    Returns stores where the user is a team member (not the owner).

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        A list of Store ORM instances accessible through team membership.
    """
    result = await db.execute(
        select(Store)
        .join(TeamMember, TeamMember.store_id == Store.id)
        .where(
            TeamMember.user_id == user_id,
            Store.status != StoreStatus.deleted,
        )
        .order_by(Store.created_at.desc())
    )
    return list(result.scalars().all())


async def check_store_access(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
) -> str | None:
    """Check if a user has access to a store via team membership.

    First checks if the user is the store owner (returns ``"owner"``),
    then checks for a team membership and returns the assigned role.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The user's UUID.

    Returns:
        The role string (``"owner"``, ``"admin"``, ``"editor"``,
        ``"viewer"``) or None if the user has no access.
    """
    # Check direct ownership first
    store_result = await db.execute(
        select(Store).where(
            Store.id == store_id,
            Store.status != StoreStatus.deleted,
        )
    )
    store = store_result.scalar_one_or_none()
    if store is None:
        return None

    if store.user_id == user_id:
        return "owner"

    # Check team membership
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.store_id == store_id,
            TeamMember.user_id == user_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if member is not None:
        return member.role

    return None
