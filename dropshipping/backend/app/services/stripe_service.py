"""Stripe integration service.

Handles Stripe Checkout session creation, subscription management,
Customer Portal, and webhook event verification via the Stripe Python SDK.

**For Developers:**
    ``create_checkout_session`` builds a Stripe Checkout session from
    validated order items. ``create_subscription_session`` creates a
    subscription-mode checkout. ``construct_webhook_event`` verifies
    webhook signatures. If ``STRIPE_SECRET_KEY`` is empty, all functions
    return mock data for local development without Stripe.

**For QA Engineers:**
    - Checkout creates a Stripe session with line items matching the cart.
    - Prices are converted to cents (Stripe uses smallest currency unit).
    - Webhook signature verification protects against spoofed events.
    - In dev mode (no Stripe key), mock checkout/portal URLs are returned.

**For End Users:**
    When you click "Checkout" or "Subscribe", you'll be redirected to a
    secure Stripe payment page. After payment, you'll be redirected back.
"""

import uuid

import stripe

from app.config import settings


def create_checkout_session(
    order_id: uuid.UUID,
    items: list[dict],
    customer_email: str,
    store_name: str,
    total_override: "Decimal | None" = None,
) -> dict:
    """Create a Stripe Checkout session for an order.

    If ``total_override`` is provided (because discounts, tax, or gift cards
    changed the total), Stripe is sent a single line item representing the
    adjusted total rather than individual product line items. This ensures
    the amount Stripe charges matches the order total exactly.

    If the Stripe secret key is not configured, returns a mock session
    for local development.

    Args:
        order_id: The UUID of the pending order.
        items: List of order item dicts with product_title, unit_price, quantity.
        customer_email: Customer's email for Stripe receipts.
        store_name: Store name for display on the checkout page.
        total_override: If set, charge this exact amount instead of
            summing individual line items. Used when discounts, tax,
            or gift cards modify the total.

    Returns:
        A dict with ``session_id`` and ``checkout_url``.

    Raises:
        stripe.error.StripeError: If the Stripe API call fails.
    """
    if not settings.stripe_secret_key:
        # Mock mode for local dev without Stripe keys
        mock_session_id = f"cs_test_mock_{order_id}"
        return {
            "session_id": mock_session_id,
            "checkout_url": settings.stripe_success_url.replace(
                "{CHECKOUT_SESSION_ID}", mock_session_id
            ),
        }

    stripe.api_key = settings.stripe_secret_key

    if total_override is not None:
        # When adjustments exist, send a single line item with the final total
        line_items = [{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"Order from {store_name}",
                },
                "unit_amount": int(total_override * 100),
            },
            "quantity": 1,
        }]
    else:
        line_items = []
        for item in items:
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": item["product_title"],
                    },
                    "unit_amount": int(item["unit_price"] * 100),
                },
                "quantity": item["quantity"],
            })

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        customer_email=customer_email,
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        metadata={
            "order_id": str(order_id),
            "store_name": store_name,
        },
    )

    return {
        "session_id": session.id,
        "checkout_url": session.url,
    }


def construct_webhook_event(
    payload: bytes,
    sig_header: str,
) -> dict:
    """Verify and construct a Stripe webhook event from the raw payload.

    In mock mode (no webhook secret configured), parses the JSON payload
    directly without signature verification. This allows local development
    and testing to work without real Stripe keys.

    Args:
        payload: Raw request body bytes.
        sig_header: The ``Stripe-Signature`` header value.

    Returns:
        A dict (or Stripe Event) with ``type`` and ``data.object`` keys.

    Raises:
        stripe.error.SignatureVerificationError: If the signature is invalid
            (real mode only).
    """
    import json

    if not settings.stripe_webhook_secret:
        # Mock mode: parse JSON directly without signature verification
        return json.loads(payload)

    stripe.api_key = settings.stripe_secret_key

    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )
    return event


def create_stripe_customer(email: str, metadata: dict | None = None) -> str:
    """Create a Stripe Customer object and return its ID.

    In mock mode, returns a deterministic mock customer ID.

    Args:
        email: Customer email address.
        metadata: Optional metadata to attach to the Customer.

    Returns:
        The Stripe Customer ID string.
    """
    if not settings.stripe_secret_key:
        return f"cus_mock_{uuid.uuid4().hex[:12]}"

    stripe.api_key = settings.stripe_secret_key
    customer = stripe.Customer.create(
        email=email,
        metadata=metadata or {},
    )
    return customer.id


def create_subscription_session(
    customer_id: str,
    price_id: str,
    trial_days: int,
    success_url: str,
    cancel_url: str,
    metadata: dict | None = None,
) -> dict:
    """Create a Stripe Checkout session in subscription mode.

    In mock mode, returns a mock session that redirects directly to the
    success URL, simulating a completed subscription checkout.

    Args:
        customer_id: Stripe Customer ID.
        price_id: Stripe Price ID for the subscription plan.
        trial_days: Number of free-trial days (0 for no trial).
        success_url: URL to redirect to after successful payment.
        cancel_url: URL to redirect to if the user cancels.
        metadata: Optional metadata for the session.

    Returns:
        A dict with ``session_id`` and ``checkout_url``.
    """
    if not settings.stripe_secret_key:
        mock_session_id = f"cs_sub_mock_{uuid.uuid4().hex[:12]}"
        return {
            "session_id": mock_session_id,
            "checkout_url": success_url,
        }

    stripe.api_key = settings.stripe_secret_key

    session_params: dict = {
        "customer": customer_id,
        "payment_method_types": ["card"],
        "line_items": [{"price": price_id, "quantity": 1}],
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": metadata or {},
    }

    if trial_days > 0:
        session_params["subscription_data"] = {
            "trial_period_days": trial_days,
        }

    session = stripe.checkout.Session.create(**session_params)
    return {
        "session_id": session.id,
        "checkout_url": session.url,
    }


def create_billing_portal_session(
    customer_id: str,
    return_url: str,
) -> dict:
    """Create a Stripe Customer Portal session for subscription management.

    In mock mode, returns the ``return_url`` as the portal URL.

    Args:
        customer_id: Stripe Customer ID.
        return_url: URL to redirect to when the user exits the portal.

    Returns:
        A dict with ``portal_url``.
    """
    if not settings.stripe_secret_key:
        return {"portal_url": return_url}

    stripe.api_key = settings.stripe_secret_key
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return {"portal_url": session.url}
