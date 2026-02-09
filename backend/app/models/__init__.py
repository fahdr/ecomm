"""SQLAlchemy ORM models.

All models are imported here so that Alembic can discover them via
``Base.metadata`` when autogenerating migrations.

**Model inventory (Phase 1 features F1-F31):**

Core models:
    - User: Platform user accounts and authentication.
    - Store, StoreStatus: User-created dropshipping stores.
    - Product, ProductStatus, ProductVariant: Store product catalog.
    - Order, OrderItem, OrderStatus: Customer orders and line items.
    - Subscription, SubscriptionStatus: Stripe subscription billing.

Feature models:
    - Discount, DiscountProduct, DiscountCategory, DiscountUsage (F8):
      Coupon codes and promotional discounts.
    - Category, ProductCategory (F9): Hierarchical product categories.
    - Supplier, ProductSupplier (F10): Dropshipping supplier management.
    - Review, ReviewStatus (F12): Customer product reviews with moderation.
    - Refund, RefundStatus, RefundReason (F14): Order refund processing.
    - TaxRate (F16): Location-based tax rate configuration.
    - Upsell, UpsellType (F18): Product upsell/cross-sell recommendations.
    - Segment, SegmentCustomer, SegmentType (F19): Customer segmentation.
    - GiftCard, GiftCardTransaction, GiftCardStatus (F20): Store gift cards.
    - CustomDomain, DomainStatus (F22): Custom domain management.
    - StoreWebhook, WebhookDelivery, WebhookEvent (F23): Store webhooks.
    - TeamMember, TeamInvite, TeamRole (F24): Multi-user store access.
    - Notification, NotificationType (F25): In-app notifications.
    - FraudCheck, FraudRiskLevel (F28): Order fraud detection.
    - ABTest, ABTestVariant, ABTestStatus (F29): A/B testing experiments.
    - CustomerAccount, CustomerWishlist (F7.5): Storefront customer accounts
      and wishlists.
"""

# Core models
from app.models.user import User  # noqa: F401
from app.models.store import Store, StoreStatus  # noqa: F401
from app.models.product import Product, ProductStatus, ProductVariant  # noqa: F401
from app.models.order import Order, OrderItem, OrderStatus  # noqa: F401
from app.models.subscription import Subscription, SubscriptionStatus  # noqa: F401

# F8 - Discounts
from app.models.discount import (  # noqa: F401
    Discount,
    DiscountCategory,
    DiscountProduct,
    DiscountStatus,
    DiscountType,
    DiscountUsage,
    AppliesTo,
)

# F9 - Categories
from app.models.category import Category, ProductCategory  # noqa: F401

# F10 - Supplier Management
from app.models.supplier import (  # noqa: F401
    Supplier,
    SupplierStatus,
    ProductSupplier,
)

# F12 - Reviews
from app.models.review import Review, ReviewStatus  # noqa: F401

# F14 - Refunds
from app.models.refund import Refund, RefundStatus, RefundReason  # noqa: F401

# F16 - Tax
from app.models.tax import TaxRate  # noqa: F401

# F18 - Upsells
from app.models.upsell import Upsell, UpsellType  # noqa: F401

# F19 - Segments
from app.models.segment import Segment, SegmentCustomer, SegmentType  # noqa: F401

# F20 - Gift Cards
from app.models.gift_card import (  # noqa: F401
    GiftCard,
    GiftCardStatus,
    GiftCardTransaction,
    TransactionType,
)

# F22 - Custom Domains
from app.models.domain import CustomDomain, DomainStatus  # noqa: F401

# F23 - Store Webhooks
from app.models.webhook import (  # noqa: F401
    StoreWebhook,
    WebhookDelivery,
    WebhookEvent,
)

# F24 - Teams
from app.models.team import TeamMember, TeamInvite, TeamRole  # noqa: F401

# F25 - Notifications
from app.models.notification import Notification, NotificationType  # noqa: F401

# F28 - Fraud Detection
from app.models.fraud import FraudCheck, FraudRiskLevel  # noqa: F401

# F29 - A/B Testing
from app.models.ab_test import ABTest, ABTestVariant, ABTestStatus  # noqa: F401

# F7.5 - Storefront Customer Accounts
from app.models.customer import CustomerAccount, CustomerWishlist  # noqa: F401

# F15 - Store Themes (enhanced with JSON config, blocks, and presets)
from app.models.theme import StoreTheme  # noqa: F401
