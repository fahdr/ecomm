"""Onboarding checklist API for new users.

Provides a single endpoint that returns the authenticated user's onboarding
progress as a checklist with completion percentage. Each step corresponds
to a key milestone in setting up a dropshipping store.

**For Developers:**
    The router is prefixed with ``/onboarding`` and mounted under ``/api/v1``
    in ``main.py``. Authentication is enforced via the shared
    ``get_current_user`` dependency from ``app.api.deps``.

**For QA Engineers:**
    - ``GET /api/v1/onboarding/checklist`` requires a valid Bearer token.
    - A brand-new user with no stores returns all steps as ``false`` and 0%.
    - Creating a store flips ``create_store`` to ``true`` (20%).
    - Adding a product flips ``add_products`` to ``true`` (40%).

**For Project Managers:**
    The onboarding checklist drives the new-user experience in the dashboard.
    It guides merchants through the essential first steps and tracks their
    progress toward a fully operational store.

**For End Users:**
    After signing up, the onboarding checklist shows you what to do next:
    create a store, add products, customize your theme, connect a domain,
    and get your first order.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.store import Store
from app.models.product import Product
from app.models.order import Order
from app.models.domain import CustomDomain
from app.models.theme import StoreTheme
from app.models.user import User

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/checklist")
async def get_onboarding_checklist(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the user's onboarding progress checklist.

    Queries the database for key milestones that indicate a merchant has
    completed the essential setup steps for their first store. Each step
    is a boolean flag, and an overall completion percentage is computed.

    Checks:
        - ``create_store``: User has created at least one store.
        - ``add_products``: The first store has at least one product.
        - ``customize_theme``: The first store has a StoreTheme record.
        - ``connect_domain``: The first store has a CustomDomain record.
        - ``first_order``: The first store has at least one order.

    Args:
        db: Async database session injected by FastAPI.
        current_user: The authenticated user, resolved from the JWT token.

    Returns:
        dict: A JSON object containing the checklist steps, completed count,
        total steps, and completion percentage.
    """
    user_id = current_user.id

    # Query the user's first store
    stores_result = await db.execute(
        select(Store).where(Store.user_id == user_id).limit(1)
    )
    store = stores_result.scalar_one_or_none()

    has_store = store is not None
    has_products = False
    has_theme = False
    has_domain = False
    has_order = False

    if store:
        # Check products
        prod_count = await db.execute(
            select(func.count()).select_from(Product).where(
                Product.store_id == store.id
            )
        )
        has_products = (prod_count.scalar() or 0) > 0

        # Check theme customization (has a StoreTheme record)
        try:
            theme_result = await db.execute(
                select(StoreTheme).where(
                    StoreTheme.store_id == store.id
                ).limit(1)
            )
            has_theme = theme_result.scalar_one_or_none() is not None
        except Exception:
            has_theme = False

        # Check custom domain
        try:
            domain_result = await db.execute(
                select(CustomDomain).where(
                    CustomDomain.store_id == store.id
                ).limit(1)
            )
            has_domain = domain_result.scalar_one_or_none() is not None
        except Exception:
            has_domain = False

        # Check orders
        order_count = await db.execute(
            select(func.count()).select_from(Order).where(
                Order.store_id == store.id
            )
        )
        has_order = (order_count.scalar() or 0) > 0

    steps = [has_store, has_products, has_theme, has_domain, has_order]
    completed = sum(1 for s in steps if s)

    return {
        "checklist": {
            "create_store": {"done": has_store, "label": "Create your first store"},
            "add_products": {"done": has_products, "label": "Add your first product"},
            "customize_theme": {"done": has_theme, "label": "Customize your store theme"},
            "connect_domain": {"done": has_domain, "label": "Connect a custom domain"},
            "first_order": {"done": has_order, "label": "Receive your first order"},
        },
        "completed": completed,
        "total": len(steps),
        "completion_percentage": int((completed / len(steps)) * 100) if steps else 0,
    }
