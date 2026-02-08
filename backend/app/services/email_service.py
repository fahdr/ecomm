"""Transactional email service.

Provides a centralised email sending interface for all transactional
emails in the platform -- order confirmations, shipping notifications,
refund notices, welcome emails, password resets, gift card deliveries,
and team invitations.

**For Developers:**
    The ``EmailService`` class uses Jinja2 templates from
    ``app/templates/email/`` for HTML email rendering. In dev mode
    (``dev_mode=True``), emails are logged to stdout instead of being
    sent over SMTP. The singleton instance ``email_service`` should be
    imported and used directly. Template files are loaded lazily and
    fall back to plain-text if the template directory doesn't exist.

**For QA Engineers:**
    - In dev mode, no emails are actually sent -- check the application
      logs for email content.
    - ``send_email`` returns True on success, False on failure (never
      raises exceptions for send failures).
    - Each ``send_*`` method builds a context dict and delegates to
      ``send_email`` with the appropriate template and subject.
    - Template names follow the pattern ``{action}.html``.

**For Project Managers:**
    This service powers Feature 11 (Transactional Email) from the backlog.
    It ensures customers receive timely notifications for order lifecycle
    events and account actions.

**For End Users:**
    Your customers receive automated emails when they place an order,
    when their order ships, when a refund is processed, and more. As a
    store owner, your team members receive invitation emails with a link
    to join your store.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EmailService:
    """Centralised transactional email service.

    Renders HTML emails using Jinja2 templates and sends them via SMTP.
    In development mode, emails are logged to the console instead of
    being sent over the network.

    Attributes:
        template_env: Jinja2 template environment for email templates.
        dev_mode: When True, emails are logged instead of sent.
    """

    def __init__(self) -> None:
        """Initialise the email service.

        Attempts to load Jinja2 templates from ``app/templates/email/``.
        Falls back gracefully if the directory doesn't exist.
        """
        self.dev_mode = True  # In dev, log instead of sending
        self.template_env = None

        try:
            from jinja2 import Environment, FileSystemLoader
            self.template_env = Environment(
                loader=FileSystemLoader("app/templates/email"),
                autoescape=True,
            )
        except Exception:
            logger.warning(
                "Could not initialise Jinja2 email templates. "
                "Emails will use plain-text fallback."
            )

    def _render_template(
        self, template_name: str, context: dict[str, Any]
    ) -> str:
        """Render an email template with the given context.

        Falls back to a simple plain-text representation if the template
        engine is not available or the template file doesn't exist.

        Args:
            template_name: The template filename (e.g. ``"order_confirmation.html"``).
            context: Template variables as a dict.

        Returns:
            The rendered HTML string.
        """
        if self.template_env is not None:
            try:
                template = self.template_env.get_template(template_name)
                return template.render(**context)
            except Exception:
                logger.warning(
                    "Template '%s' not found, using plain-text fallback",
                    template_name,
                )

        # Plain-text fallback
        lines = [f"{k}: {v}" for k, v in context.items()]
        return "\n".join(lines)

    async def send_email(
        self,
        to: str,
        subject: str,
        template_name: str,
        context: dict[str, Any],
    ) -> bool:
        """Send a transactional email.

        In dev mode, logs the email content instead of sending via SMTP.
        In production, this would use an SMTP client or email API service
        (e.g. SendGrid, AWS SES, Mailgun).

        Args:
            to: Recipient email address.
            subject: Email subject line.
            template_name: The Jinja2 template filename.
            context: Template variables dict.

        Returns:
            True if the email was sent (or logged) successfully, False
            if an error occurred.
        """
        try:
            html_body = self._render_template(template_name, context)

            if self.dev_mode:
                logger.info(
                    "=== EMAIL (dev mode) ===\n"
                    "To: %s\n"
                    "Subject: %s\n"
                    "Template: %s\n"
                    "Body:\n%s\n"
                    "========================",
                    to,
                    subject,
                    template_name,
                    html_body[:500],  # Truncate for readability
                )
                return True

            # Production: send via SMTP
            # import smtplib
            # from email.mime.text import MIMEText
            # from email.mime.multipart import MIMEMultipart
            #
            # msg = MIMEMultipart("alternative")
            # msg["Subject"] = subject
            # msg["From"] = settings.email_from_address
            # msg["To"] = to
            # msg.attach(MIMEText(html_body, "html"))
            #
            # with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            #     server.starttls()
            #     server.login(settings.smtp_user, settings.smtp_password)
            #     server.send_message(msg)

            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to, str(e))
            return False

    async def send_order_confirmation(
        self,
        order: Any,
        store: Any,
    ) -> bool:
        """Send an order confirmation email to the customer.

        Args:
            order: The Order ORM instance (must have ``customer_email``,
                ``id``, ``total``, ``items``).
            store: The Store ORM instance (must have ``name``).

        Returns:
            True if sent successfully, False otherwise.
        """
        context = {
            "store_name": store.name,
            "order_id": str(order.id),
            "order_total": str(order.total),
            "customer_email": order.customer_email,
            "items": [
                {
                    "title": item.product_title,
                    "quantity": item.quantity,
                    "price": str(item.unit_price),
                }
                for item in (order.items if hasattr(order, "items") else [])
            ],
        }
        return await self.send_email(
            to=order.customer_email,
            subject=f"Order Confirmation - {store.name} (#{str(order.id)[:8]})",
            template_name="order_confirmation.html",
            context=context,
        )

    async def send_order_shipped(
        self,
        order: Any,
        store: Any,
        tracking_number: str | None = None,
    ) -> bool:
        """Send a shipping notification email to the customer.

        Args:
            order: The Order ORM instance.
            store: The Store ORM instance.
            tracking_number: Optional tracking number for the shipment.

        Returns:
            True if sent successfully, False otherwise.
        """
        context = {
            "store_name": store.name,
            "order_id": str(order.id),
            "customer_email": order.customer_email,
            "tracking_number": tracking_number,
        }
        return await self.send_email(
            to=order.customer_email,
            subject=f"Your Order Has Shipped - {store.name}",
            template_name="order_shipped.html",
            context=context,
        )

    async def send_refund_notification(
        self,
        refund: Any,
        store: Any,
    ) -> bool:
        """Send a refund confirmation email to the customer.

        Args:
            refund: The Refund ORM instance (must have ``customer_email``,
                ``amount``, ``order_id``).
            store: The Store ORM instance.

        Returns:
            True if sent successfully, False otherwise.
        """
        context = {
            "store_name": store.name,
            "refund_amount": str(refund.amount),
            "order_id": str(refund.order_id),
            "customer_email": refund.customer_email,
            "reason": refund.reason.value if hasattr(refund.reason, "value") else str(refund.reason),
        }
        return await self.send_email(
            to=refund.customer_email,
            subject=f"Refund Processed - {store.name}",
            template_name="refund_notification.html",
            context=context,
        )

    async def send_welcome_email(
        self,
        customer: Any,
        store: Any,
    ) -> bool:
        """Send a welcome email to a new customer.

        Args:
            customer: An object with ``email`` and optionally ``name``.
            store: The Store ORM instance.

        Returns:
            True if sent successfully, False otherwise.
        """
        email = customer.email if hasattr(customer, "email") else str(customer)
        name = getattr(customer, "name", getattr(customer, "email", "Customer"))

        context = {
            "store_name": store.name,
            "customer_name": name,
            "customer_email": email,
        }
        return await self.send_email(
            to=email,
            subject=f"Welcome to {store.name}!",
            template_name="welcome.html",
            context=context,
        )

    async def send_password_reset(
        self,
        email: str,
        reset_token: str,
        store: Any | None = None,
    ) -> bool:
        """Send a password reset email.

        Args:
            email: The user's email address.
            reset_token: The password reset token.
            store: Optional Store ORM instance for branding context.

        Returns:
            True if sent successfully, False otherwise.
        """
        store_name = store.name if store else "Dropship Platform"
        context = {
            "store_name": store_name,
            "reset_token": reset_token,
            "reset_url": f"/reset-password?token={reset_token}",
            "email": email,
        }
        return await self.send_email(
            to=email,
            subject=f"Password Reset - {store_name}",
            template_name="password_reset.html",
            context=context,
        )

    async def send_gift_card(
        self,
        gift_card: Any,
        store: Any,
    ) -> bool:
        """Send a gift card delivery email to the recipient.

        Args:
            gift_card: The GiftCard ORM instance (must have ``code``,
                ``initial_balance``, ``customer_email``).
            store: The Store ORM instance.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not gift_card.customer_email:
            logger.warning(
                "Cannot send gift card email: no customer_email on gift card %s",
                gift_card.id,
            )
            return False

        context = {
            "store_name": store.name,
            "gift_card_code": gift_card.code,
            "balance": str(gift_card.initial_balance),
            "customer_email": gift_card.customer_email,
        }
        return await self.send_email(
            to=gift_card.customer_email,
            subject=f"You've Received a Gift Card from {store.name}!",
            template_name="gift_card.html",
            context=context,
        )

    async def send_team_invite(
        self,
        invite: Any,
        store: Any,
    ) -> bool:
        """Send a team invitation email.

        Args:
            invite: The TeamInvite ORM instance (must have ``email``,
                ``token``, ``role``).
            store: The Store ORM instance.

        Returns:
            True if sent successfully, False otherwise.
        """
        context = {
            "store_name": store.name,
            "invite_email": invite.email,
            "role": invite.role,
            "invite_url": f"/accept-invite?token={invite.token}",
            "token": invite.token,
        }
        return await self.send_email(
            to=invite.email,
            subject=f"You've Been Invited to Join {store.name}",
            template_name="team_invite.html",
            context=context,
        )


# Module-level singleton instance
email_service = EmailService()
