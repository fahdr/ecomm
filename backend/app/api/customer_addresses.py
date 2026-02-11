"""Customer addresses API router.

Provides CRUD endpoints for customers to manage their saved shipping
addresses from the storefront.

**For Developers:**
    Setting an address as default automatically unsets the previous default.
    Addresses are scoped to a customer + store pair.

**For QA Engineers:**
    - Creating an address with ``is_default: true`` unsets other defaults.
    - A customer can have multiple addresses per store.
    - Delete returns 204 on success, 404 if not found.

**For End Users:**
    Save your shipping addresses to speed up checkout. You can mark one
    as your default address.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import CustomerAccount, CustomerAddress
from app.models.store import Store, StoreStatus
from app.api.deps import get_current_customer
from app.schemas.customer import CustomerAddressRequest, CustomerAddressResponse

router = APIRouter(
    prefix="/public/stores/{slug}/customers/me/addresses",
    tags=["customer-addresses"],
)


async def _get_active_store(db: AsyncSession, slug: str) -> Store:
    """Resolve an active store by slug."""
    result = await db.execute(
        select(Store).where(Store.slug == slug, Store.status == StoreStatus.active)
    )
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.get("", response_model=list[CustomerAddressResponse])
async def list_addresses(
    slug: str,
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """List all saved addresses for the customer.

    Args:
        slug: The store's URL slug.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        List of saved addresses, default address first.
    """
    store = await _get_active_store(db, slug)

    result = await db.execute(
        select(CustomerAddress)
        .where(
            CustomerAddress.customer_id == customer.id,
            CustomerAddress.store_id == store.id,
        )
        .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
    )
    addresses = result.scalars().all()
    return [CustomerAddressResponse.model_validate(a) for a in addresses]


@router.post("", response_model=CustomerAddressResponse, status_code=status.HTTP_201_CREATED)
async def create_address(
    slug: str,
    body: CustomerAddressRequest,
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """Create a new saved address.

    If ``is_default`` is True, any existing default address for this
    customer in this store is unset.

    Args:
        slug: The store's URL slug.
        body: Address data.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        The created address.
    """
    store = await _get_active_store(db, slug)

    if body.is_default:
        await db.execute(
            update(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer.id,
                CustomerAddress.store_id == store.id,
            )
            .values(is_default=False)
        )

    address = CustomerAddress(
        customer_id=customer.id,
        store_id=store.id,
        label=body.label,
        name=body.name,
        line1=body.line1,
        line2=body.line2,
        city=body.city,
        state=body.state,
        postal_code=body.postal_code,
        country=body.country,
        phone=body.phone,
        is_default=body.is_default,
    )
    db.add(address)
    await db.commit()
    await db.refresh(address)

    return CustomerAddressResponse.model_validate(address)


@router.patch("/{address_id}", response_model=CustomerAddressResponse)
async def update_address(
    slug: str,
    address_id: uuid.UUID,
    body: CustomerAddressRequest,
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing saved address.

    Args:
        slug: The store's URL slug.
        address_id: The address UUID.
        body: Updated address data.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        The updated address.

    Raises:
        HTTPException: 404 if the address is not found.
    """
    store = await _get_active_store(db, slug)

    result = await db.execute(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer.id,
            CustomerAddress.store_id == store.id,
        )
    )
    address = result.scalar_one_or_none()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    if body.is_default and not address.is_default:
        await db.execute(
            update(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer.id,
                CustomerAddress.store_id == store.id,
                CustomerAddress.id != address_id,
            )
            .values(is_default=False)
        )

    address.label = body.label
    address.name = body.name
    address.line1 = body.line1
    address.line2 = body.line2
    address.city = body.city
    address.state = body.state
    address.postal_code = body.postal_code
    address.country = body.country
    address.phone = body.phone
    address.is_default = body.is_default

    await db.commit()
    await db.refresh(address)

    return CustomerAddressResponse.model_validate(address)


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    slug: str,
    address_id: uuid.UUID,
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved address.

    Args:
        slug: The store's URL slug.
        address_id: The address UUID.
        customer: The authenticated customer.
        db: Async database session.

    Raises:
        HTTPException: 404 if the address is not found.
    """
    store = await _get_active_store(db, slug)

    result = await db.execute(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer.id,
            CustomerAddress.store_id == store.id,
        )
    )
    address = result.scalar_one_or_none()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    await db.delete(address)
    await db.commit()


@router.post("/{address_id}/default", response_model=CustomerAddressResponse)
async def set_default(
    slug: str,
    address_id: uuid.UUID,
    customer: CustomerAccount = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """Set an address as the default.

    Args:
        slug: The store's URL slug.
        address_id: The address UUID.
        customer: The authenticated customer.
        db: Async database session.

    Returns:
        The address that was set as default.

    Raises:
        HTTPException: 404 if the address is not found.
    """
    store = await _get_active_store(db, slug)

    result = await db.execute(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer.id,
            CustomerAddress.store_id == store.id,
        )
    )
    address = result.scalar_one_or_none()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    # Unset all other defaults
    await db.execute(
        update(CustomerAddress)
        .where(
            CustomerAddress.customer_id == customer.id,
            CustomerAddress.store_id == store.id,
            CustomerAddress.id != address_id,
        )
        .values(is_default=False)
    )

    address.is_default = True
    await db.commit()
    await db.refresh(address)

    return CustomerAddressResponse.model_validate(address)
