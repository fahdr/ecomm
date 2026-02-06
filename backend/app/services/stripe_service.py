"""Stripe integration service.

Handles Stripe Checkout session creation and webhook event verification.
Uses the Stripe Python SDK for all interactions.

**For Developers:**
    ``create_checkout_session`` builds a Stripe Checkout session from
    validated order items. ``construct_webhook_event`` verifies webhook
    signatures. If ``STRIPE_SECRET_KEY`` is empty, checkout returns a
    mock session for local development without Stripe.

**For QA Engineers:**
    - Checkout creates a Stripe session with line items matching the cart.
    - Prices are converted to cents (Stripe uses smallest currency unit).
    - Webhook signature verification protects against spoofed events.
    - In dev mode (no Stripe key), a mock checkout URL is returned.

**For End Users:**
    When you click "Checkout", you'll be redirected to a secure Stripe
    payment page. After payment, you'll be redirected back to the store.
"""

import uuid

import stripe

from app.config import settings


def create_checkout_session(
    order_id: uuid.UUID,
    items: list[dict],
    customer_email: str,
    store_name: str,
) -> dict:
    """Create a Stripe Checkout session for an order.

    If the Stripe secret key is not configured, returns a mock session
    for local development.

    Args:
        order_id: The UUID of the pending order.
        items: List of order item dicts with product_title, unit_price, quantity.
        customer_email: Customer's email for Stripe receipts.
        store_name: Store name for display on the checkout page.

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
) -> stripe.Event:
    """Verify and construct a Stripe webhook event from the raw payload.

    Args:
        payload: Raw request body bytes.
        sig_header: The ``Stripe-Signature`` header value.

    Returns:
        A verified Stripe Event object.

    Raises:
        ValueError: If the webhook secret is not configured.
        stripe.error.SignatureVerificationError: If the signature is invalid.
    """
    if not settings.stripe_webhook_secret:
        raise ValueError("Stripe webhook secret not configured")

    stripe.api_key = settings.stripe_secret_key

    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )
    return event
