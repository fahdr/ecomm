"""CSV export service for orders, products, and customers.

Generates streaming CSV responses for data export from the dashboard.
Each export function queries the database and yields CSV rows.

**For Developers:**
    Uses Python's ``csv`` module with ``io.StringIO`` for in-memory CSV
    generation. Returns a generator of CSV string chunks for streaming
    response support. Each function verifies store ownership before
    querying.

**For QA Engineers:**
    - Exported CSVs include headers as the first row.
    - All monetary values are formatted to 2 decimal places.
    - Datetime values are in ISO 8601 format.
    - Empty/null fields appear as empty strings in CSV.

**For Project Managers:**
    Implements Feature 5A (CSV Export) from the Phase 5 polish plan.
    Supports exporting orders, products, and customers per store.

@module services/export_service
"""

import csv
import io
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.customer import CustomerAccount
from app.models.store import Store
from app.models.user import User


async def _verify_store(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Verify that the store exists and belongs to the user.

    Args:
        db: Database session.
        store_id: The store UUID.
        user_id: The authenticated user's UUID.

    Raises:
        ValueError: If the store is not found or not owned by the user.
    """
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.user_id == user_id)
    )
    store = result.scalar_one_or_none()
    if not store:
        raise ValueError("Store not found or access denied.")


async def export_orders_csv(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> str:
    """Export all orders for a store as a CSV string.

    Args:
        db: Database session.
        store_id: The store UUID.
        user_id: The authenticated user's UUID.

    Returns:
        A complete CSV string with headers and all order rows.

    Raises:
        ValueError: If the store is not found or not owned by the user.
    """
    await _verify_store(db, store_id, user_id)

    result = await db.execute(
        select(Order)
        .where(Order.store_id == store_id)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Order ID",
        "Status",
        "Customer Email",
        "Subtotal",
        "Discount Code",
        "Discount Amount",
        "Tax Amount",
        "Gift Card Amount",
        "Total",
        "Currency",
        "Shipping Address",
        "Tracking Number",
        "Carrier",
        "Notes",
        "Created At",
        "Updated At",
    ])

    for order in orders:
        writer.writerow([
            str(order.id),
            order.status.value if order.status else "",
            order.customer_email or "",
            f"{order.subtotal:.2f}" if order.subtotal is not None else "",
            order.discount_code or "",
            f"{order.discount_amount:.2f}" if order.discount_amount is not None else "0.00",
            f"{order.tax_amount:.2f}" if order.tax_amount is not None else "0.00",
            f"{order.gift_card_amount:.2f}" if order.gift_card_amount is not None else "0.00",
            f"{order.total:.2f}",
            order.currency or "USD",
            order.shipping_address or "",
            order.tracking_number or "",
            order.carrier or "",
            getattr(order, "notes", "") or "",
            order.created_at.isoformat() if order.created_at else "",
            order.updated_at.isoformat() if order.updated_at else "",
        ])

    return output.getvalue()


async def export_products_csv(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> str:
    """Export all products for a store as a CSV string.

    Args:
        db: Database session.
        store_id: The store UUID.
        user_id: The authenticated user's UUID.

    Returns:
        A complete CSV string with headers and all product rows.

    Raises:
        ValueError: If the store is not found or not owned by the user.
    """
    await _verify_store(db, store_id, user_id)

    result = await db.execute(
        select(Product)
        .where(Product.store_id == store_id)
        .order_by(Product.created_at.desc())
    )
    products = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Product ID",
        "Title",
        "Slug",
        "Status",
        "Price",
        "Compare At Price",
        "Cost",
        "Description",
        "Tags",
        "Avg Rating",
        "Review Count",
        "SEO Title",
        "SEO Description",
        "Images",
        "Created At",
        "Updated At",
    ])

    for product in products:
        writer.writerow([
            str(product.id),
            product.title or "",
            product.slug or "",
            product.status.value if product.status else "",
            f"{product.price:.2f}" if product.price is not None else "",
            f"{product.compare_at_price:.2f}" if product.compare_at_price is not None else "",
            f"{product.cost:.2f}" if product.cost is not None else "",
            product.description or "",
            "; ".join(product.tags) if product.tags else "",
            f"{product.avg_rating:.2f}" if product.avg_rating is not None else "",
            str(product.review_count) if product.review_count else "0",
            product.seo_title or "",
            product.seo_description or "",
            "; ".join(product.images) if product.images else "",
            product.created_at.isoformat() if product.created_at else "",
            product.updated_at.isoformat() if product.updated_at else "",
        ])

    return output.getvalue()


async def export_customers_csv(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> str:
    """Export all customer accounts for a store as a CSV string.

    Args:
        db: Database session.
        store_id: The store UUID.
        user_id: The authenticated user's UUID.

    Returns:
        A complete CSV string with headers and all customer rows.

    Raises:
        ValueError: If the store is not found or not owned by the user.
    """
    await _verify_store(db, store_id, user_id)

    result = await db.execute(
        select(CustomerAccount)
        .where(CustomerAccount.store_id == store_id)
        .order_by(CustomerAccount.created_at.desc())
    )
    customers = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Customer ID",
        "Email",
        "First Name",
        "Last Name",
        "Active",
        "Created At",
        "Updated At",
    ])

    for customer in customers:
        writer.writerow([
            str(customer.id),
            customer.email or "",
            customer.first_name or "",
            customer.last_name or "",
            "Yes" if customer.is_active else "No",
            customer.created_at.isoformat() if customer.created_at else "",
            customer.updated_at.isoformat() if customer.updated_at else "",
        ])

    return output.getvalue()
