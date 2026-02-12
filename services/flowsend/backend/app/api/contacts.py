"""
Contact management API endpoints.

Provides CRUD operations for contacts and contact lists, including
bulk import, tag management, and pagination.

For Developers:
    All endpoints require authentication via `get_current_user`.
    Contact creation checks plan limits (`max_secondary`).
    Import supports both email list and CSV data.

For QA Engineers:
    Test: create, list (pagination, search, tag filter), get, update,
    delete, import (emails + CSV), plan limit enforcement.

For Project Managers:
    Contact management is foundational — all campaigns and flows
    target contacts. Import simplifies onboarding.

For End Users:
    Add your subscribers, organize them with tags, and import
    contacts in bulk from email lists or CSV files.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.email import (
    ContactCreate,
    ContactImportRequest,
    ContactImportResponse,
    ContactListCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
    PaginatedResponse,
)
from app.services.contact_service import (
    create_contact,
    create_contact_list,
    delete_contact,
    delete_contact_list,
    get_contact,
    get_contact_count,
    get_contact_list,
    get_contact_lists,
    get_contacts,
    import_contacts,
    update_contact,
)

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post("", response_model=ContactResponse, status_code=201)
async def create_contact_endpoint(
    body: ContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new contact.

    Checks plan limits before creation. Rejects duplicate emails per user.

    Args:
        body: Contact creation data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created contact.

    Raises:
        HTTPException 400: If plan limit reached or duplicate email.
    """
    try:
        contact = await create_contact(
            db, current_user, body.email,
            first_name=body.first_name, last_name=body.last_name,
            tags=body.tags, custom_fields=body.custom_fields,
        )
        return contact
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=PaginatedResponse[ContactResponse])
async def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    tag: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List contacts with pagination, search, and tag filtering.

    Args:
        page: Page number (1-indexed, default 1).
        page_size: Items per page (1-100, default 50).
        search: Optional email/name search query.
        tag: Optional tag to filter by.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of contacts.
    """
    contacts, total = await get_contacts(
        db, current_user.id, page=page, page_size=page_size,
        search=search, tag=tag,
    )
    return PaginatedResponse(
        items=contacts, total=total, page=page, page_size=page_size
    )


@router.get("/count")
async def get_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the total contact count for the current user.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Dict with 'count' key.
    """
    count = await get_contact_count(db, current_user.id)
    return {"count": count}


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact_endpoint(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single contact by ID.

    Args:
        contact_id: The contact's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The contact data.

    Raises:
        HTTPException 404: If contact not found.
    """
    contact = await get_contact(db, current_user.id, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact_endpoint(
    contact_id: uuid.UUID,
    body: ContactUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a contact's fields.

    Only provided fields are updated.

    Args:
        contact_id: The contact's UUID.
        body: Update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated contact.

    Raises:
        HTTPException 404: If contact not found.
    """
    contact = await get_contact(db, current_user.id, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    updated = await update_contact(
        db, contact,
        email=body.email, first_name=body.first_name,
        last_name=body.last_name, tags=body.tags,
        custom_fields=body.custom_fields, is_subscribed=body.is_subscribed,
    )
    return updated


@router.delete("/{contact_id}", status_code=204)
async def delete_contact_endpoint(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a contact.

    Args:
        contact_id: The contact's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If contact not found.
    """
    contact = await get_contact(db, current_user.id, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await delete_contact(db, contact)


@router.post("/import", response_model=ContactImportResponse)
async def import_contacts_endpoint(
    body: ContactImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk import contacts from email list or CSV data.

    Deduplicates against existing contacts. Respects plan limits.

    Args:
        body: Import data (emails list and/or CSV string).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Import result with imported, skipped, and total counts.
    """
    result = await import_contacts(
        db, current_user,
        emails=body.emails, csv_data=body.csv_data,
        tags=body.tags,
    )
    return ContactImportResponse(**result)


# ── Contact Lists ────────────────────────────────────────────────────────

@router.post("/lists", response_model=ContactListResponse, status_code=201)
async def create_list_endpoint(
    body: ContactListCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new contact list.

    Args:
        body: List creation data (name, description, type, rules).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created contact list.
    """
    contact_list = await create_contact_list(
        db, current_user, body.name,
        description=body.description, list_type=body.list_type,
        rules=body.rules,
    )
    return contact_list


@router.get("/lists", response_model=PaginatedResponse[ContactListResponse])
async def list_contact_lists(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List contact lists with pagination.

    Args:
        page: Page number.
        page_size: Items per page.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of contact lists.
    """
    lists, total = await get_contact_lists(
        db, current_user.id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=lists, total=total, page=page, page_size=page_size
    )


@router.delete("/lists/{list_id}", status_code=204)
async def delete_list_endpoint(
    list_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a contact list.

    Args:
        list_id: The list's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If list not found.
    """
    contact_list = await get_contact_list(db, current_user.id, list_id)
    if not contact_list:
        raise HTTPException(status_code=404, detail="Contact list not found")
    await delete_contact_list(db, contact_list)
