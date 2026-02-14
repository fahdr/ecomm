"""
Contact management service.

Handles CRUD operations for contacts and contact lists, including
bulk import, tag management, and plan limit enforcement.

For Developers:
    - All functions take an AsyncSession and user context.
    - `check_contact_limit` enforces the `max_secondary` plan limit.
    - Import deduplicates on (user_id, email) pairs.
    - CSV import expects columns: email, first_name, last_name.

For QA Engineers:
    Test: create/read/update/delete contacts, import from email list,
    import from CSV, tag add/remove, plan limit enforcement, pagination.

For Project Managers:
    Contact limits are a key differentiator between plan tiers.
    Free: 250 contacts, Pro: 10,000, Enterprise: unlimited.
"""

import csv
import io
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PLAN_LIMITS
from app.models.contact import Contact, ContactList
from app.models.user import User


async def check_contact_limit(db: AsyncSession, user: User) -> bool:
    """
    Check if the user has reached their plan's contact limit.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        True if the user can add more contacts, False if at limit.
    """
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_secondary == -1:
        return True

    result = await db.execute(
        select(func.count(Contact.id)).where(Contact.user_id == user.id)
    )
    current_count = result.scalar() or 0
    return current_count < plan_limits.max_secondary


async def get_contact_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Get the total number of contacts for a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Integer count of contacts.
    """
    result = await db.execute(
        select(func.count(Contact.id)).where(Contact.user_id == user_id)
    )
    return result.scalar() or 0


async def create_contact(
    db: AsyncSession, user: User, email: str,
    first_name: str | None = None, last_name: str | None = None,
    tags: list[str] | None = None, custom_fields: dict | None = None,
) -> Contact:
    """
    Create a new contact for the user.

    Enforces plan limits and prevents duplicate emails per user.

    Args:
        db: Async database session.
        user: The owning user.
        email: Contact's email address.
        first_name: Contact's first name (optional).
        last_name: Contact's last name (optional).
        tags: List of tags (optional).
        custom_fields: Custom metadata (optional).

    Returns:
        The newly created Contact.

    Raises:
        ValueError: If plan limit is reached or email already exists.
    """
    if not await check_contact_limit(db, user):
        raise ValueError("Contact limit reached for your plan")

    # Check duplicate
    result = await db.execute(
        select(Contact).where(
            Contact.user_id == user.id, Contact.email == email
        )
    )
    if result.scalar_one_or_none():
        raise ValueError(f"Contact with email {email} already exists")

    contact = Contact(
        user_id=user.id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        tags=tags or [],
        custom_fields=custom_fields or {},
    )
    db.add(contact)
    await db.flush()
    await db.refresh(contact)
    return contact


async def get_contacts(
    db: AsyncSession, user_id: uuid.UUID,
    page: int = 1, page_size: int = 50,
    search: str | None = None, tag: str | None = None,
) -> tuple[list[Contact], int]:
    """
    List contacts with pagination, search, and tag filtering.

    Args:
        db: Async database session.
        user_id: The owning user's UUID.
        page: Page number (1-indexed).
        page_size: Items per page.
        search: Optional email/name search query.
        tag: Optional tag to filter by.

    Returns:
        Tuple of (list of contacts, total count).
    """
    query = select(Contact).where(Contact.user_id == user_id)
    count_query = select(func.count(Contact.id)).where(Contact.user_id == user_id)

    if search:
        search_filter = Contact.email.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if tag:
        tag_filter = Contact.tags.any(tag)
        query = query.where(tag_filter)
        count_query = count_query.where(tag_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Contact.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    contacts = list(result.scalars().all())

    return contacts, total


async def get_contact(
    db: AsyncSession, user_id: uuid.UUID, contact_id: uuid.UUID
) -> Contact | None:
    """
    Get a single contact by ID, scoped to user.

    Args:
        db: Async database session.
        user_id: The owning user's UUID.
        contact_id: The contact's UUID.

    Returns:
        The Contact if found, None otherwise.
    """
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id, Contact.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def update_contact(
    db: AsyncSession, contact: Contact,
    email: str | None = None, first_name: str | None = None,
    last_name: str | None = None, tags: list[str] | None = None,
    custom_fields: dict | None = None, is_subscribed: bool | None = None,
) -> Contact:
    """
    Update an existing contact's fields.

    Only non-None parameters are applied.

    Args:
        db: Async database session.
        contact: The contact to update.
        email: New email (optional).
        first_name: New first name (optional).
        last_name: New last name (optional).
        tags: New tag list (optional, replaces existing).
        custom_fields: New custom fields (optional, replaces existing).
        is_subscribed: New subscription status (optional).

    Returns:
        The updated Contact.
    """
    if email is not None:
        contact.email = email
    if first_name is not None:
        contact.first_name = first_name
    if last_name is not None:
        contact.last_name = last_name
    if tags is not None:
        contact.tags = tags
    if custom_fields is not None:
        contact.custom_fields = custom_fields
    if is_subscribed is not None:
        contact.is_subscribed = is_subscribed
        if not is_subscribed:
            from datetime import UTC, datetime
            contact.unsubscribed_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(contact)
    return contact


async def delete_contact(db: AsyncSession, contact: Contact) -> None:
    """
    Delete a contact.

    Args:
        db: Async database session.
        contact: The contact to delete.
    """
    await db.delete(contact)
    await db.flush()


async def import_contacts(
    db: AsyncSession, user: User,
    emails: list[str] | None = None, csv_data: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """
    Bulk import contacts from a list of emails or CSV data.

    Deduplicates against existing contacts for this user. Respects plan limits.

    Args:
        db: Async database session.
        user: The owning user.
        emails: List of email addresses to import.
        csv_data: Raw CSV string with email, first_name, last_name columns.
        tags: Tags to apply to all imported contacts.

    Returns:
        Dict with 'imported', 'skipped', and 'total' counts.
    """
    records: list[dict] = []

    if emails:
        records = [{"email": e, "first_name": None, "last_name": None} for e in emails]

    if csv_data:
        reader = csv.DictReader(io.StringIO(csv_data))
        for row in reader:
            email = row.get("email", "").strip()
            if email:
                records.append({
                    "email": email,
                    "first_name": row.get("first_name", "").strip() or None,
                    "last_name": row.get("last_name", "").strip() or None,
                })

    imported = 0
    skipped = 0

    for record in records:
        # Check plan limit
        if not await check_contact_limit(db, user):
            skipped += len(records) - imported - skipped
            break

        # Check duplicate
        result = await db.execute(
            select(Contact).where(
                Contact.user_id == user.id,
                Contact.email == record["email"],
            )
        )
        if result.scalar_one_or_none():
            skipped += 1
            continue

        contact = Contact(
            user_id=user.id,
            email=record["email"],
            first_name=record["first_name"],
            last_name=record["last_name"],
            tags=tags or [],
        )
        db.add(contact)
        imported += 1

    await db.flush()

    return {"imported": imported, "skipped": skipped, "total": len(records)}


# ── Contact List Operations ──────────────────────────────────────────────

async def create_contact_list(
    db: AsyncSession, user: User, name: str,
    description: str | None = None, list_type: str = "static",
    rules: dict | None = None,
) -> ContactList:
    """
    Create a new contact list.

    Args:
        db: Async database session.
        user: The owning user.
        name: List name.
        description: List description (optional).
        list_type: "static" or "dynamic".
        rules: Filter rules for dynamic lists (optional).

    Returns:
        The newly created ContactList.
    """
    contact_list = ContactList(
        user_id=user.id,
        name=name,
        description=description,
        list_type=list_type,
        rules=rules,
    )
    db.add(contact_list)
    await db.flush()
    await db.refresh(contact_list)
    return contact_list


async def get_contact_lists(
    db: AsyncSession, user_id: uuid.UUID,
    page: int = 1, page_size: int = 50,
) -> tuple[list[ContactList], int]:
    """
    List contact lists with pagination.

    Args:
        db: Async database session.
        user_id: The owning user's UUID.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Tuple of (list of ContactList, total count).
    """
    count_result = await db.execute(
        select(func.count(ContactList.id)).where(ContactList.user_id == user_id)
    )
    total = count_result.scalar() or 0

    query = (
        select(ContactList)
        .where(ContactList.user_id == user_id)
        .order_by(ContactList.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    lists = list(result.scalars().all())

    return lists, total


async def get_contact_list(
    db: AsyncSession, user_id: uuid.UUID, list_id: uuid.UUID
) -> ContactList | None:
    """
    Get a single contact list by ID, scoped to user.

    Args:
        db: Async database session.
        user_id: The owning user's UUID.
        list_id: The list's UUID.

    Returns:
        The ContactList if found, None otherwise.
    """
    result = await db.execute(
        select(ContactList).where(
            ContactList.id == list_id, ContactList.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def delete_contact_list(db: AsyncSession, contact_list: ContactList) -> None:
    """
    Delete a contact list.

    Args:
        db: Async database session.
        contact_list: The list to delete.
    """
    await db.delete(contact_list)
    await db.flush()
