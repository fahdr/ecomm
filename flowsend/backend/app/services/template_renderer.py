"""
Jinja2-based email template rendering engine for FlowSend.

Renders email templates with variable substitution for personalized
email content. Supports both custom user HTML and built-in templates
for common email marketing scenarios.

For Developers:
    - ``render_template()`` renders a built-in template name with variables.
    - ``render_html()`` renders arbitrary HTML string with Jinja2 variables.
    - Built-in templates are defined as constants below (no filesystem needed).
    - Variables use double-brace syntax: ``{{ first_name }}``.
    - The renderer strips HTML tags to auto-generate plain-text fallbacks.

For QA Engineers:
    Test: variable substitution, missing variable handling (renders as empty),
    all built-in template names, HTML-to-plaintext conversion, XSS safety.

For Project Managers:
    Template rendering enables personalized emails at scale. Built-in
    templates cover common use cases (welcome, order confirmation, etc.)
    to reduce time-to-first-campaign for new users.

For End Users:
    Personalize your emails with dynamic variables like subscriber names,
    product details, and unsubscribe links. Choose from pre-built templates
    or create your own.
"""

import html
import re

from jinja2 import BaseLoader, Environment, Undefined


class _SilentUndefined(Undefined):
    """
    Custom Jinja2 Undefined that renders missing variables as empty strings.

    Prevents template errors when a variable is not provided. This is
    intentional for email marketing: missing personalization should
    silently degrade rather than break the email.
    """

    def __str__(self) -> str:
        """Return empty string for undefined variables."""
        return ""

    def __iter__(self):
        """Return empty iterator for undefined variables."""
        return iter([])

    def __bool__(self) -> bool:
        """Return False for undefined variables."""
        return False


# Jinja2 environment configured for email template rendering
_env = Environment(
    loader=BaseLoader(),
    undefined=_SilentUndefined,
    autoescape=True,
)


# ── Built-in email templates ──────────────────────────────────────────────

BUILTIN_TEMPLATES: dict[str, dict[str, str]] = {
    "welcome": {
        "subject": "Welcome to {{ store_name }}!",
        "html": """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #2d3748;">Welcome, {{ first_name }}!</h1>
  <p>Thank you for joining <strong>{{ store_name }}</strong>. We're excited to have you on board.</p>
  <p>Explore our latest products and exclusive offers designed just for you.</p>
  <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
  <p style="font-size: 12px; color: #718096;">
    <a href="{{ unsubscribe_url }}">Unsubscribe</a>
  </p>
</body>
</html>""",
    },
    "order_confirmation": {
        "subject": "Order Confirmed - {{ product_name }}",
        "html": """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #2d3748;">Order Confirmed!</h1>
  <p>Hi {{ first_name }},</p>
  <p>Your order for <strong>{{ product_name }}</strong> has been confirmed.</p>
  <p>We'll send you a shipping notification once your order is on its way.</p>
  <p><a href="{{ product_url }}" style="color: #3182ce;">View Order Details</a></p>
  <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
  <p style="font-size: 12px; color: #718096;">
    <a href="{{ unsubscribe_url }}">Unsubscribe</a>
  </p>
</body>
</html>""",
    },
    "shipping_notification": {
        "subject": "Your order is on its way!",
        "html": """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #2d3748;">Your Order Has Shipped!</h1>
  <p>Hi {{ first_name }},</p>
  <p>Great news! Your order for <strong>{{ product_name }}</strong> has shipped.</p>
  <p><a href="{{ product_url }}" style="color: #3182ce;">Track Your Package</a></p>
  <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
  <p style="font-size: 12px; color: #718096;">
    <a href="{{ unsubscribe_url }}">Unsubscribe</a>
  </p>
</body>
</html>""",
    },
    "abandoned_cart": {
        "subject": "You left something behind, {{ first_name }}!",
        "html": """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #2d3748;">Forgot Something?</h1>
  <p>Hi {{ first_name }},</p>
  <p>You left <strong>{{ product_name }}</strong> in your cart. It's still waiting for you!</p>
  <p><a href="{{ product_url }}" style="display: inline-block; background: #3182ce; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">Complete Your Purchase</a></p>
  <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
  <p style="font-size: 12px; color: #718096;">
    <a href="{{ unsubscribe_url }}">Unsubscribe</a>
  </p>
</body>
</html>""",
    },
    "promotional": {
        "subject": "Special Offer from {{ store_name }}",
        "html": """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #2d3748;">Exclusive Offer!</h1>
  <p>Hi {{ first_name }},</p>
  <p>Check out our latest offer on <strong>{{ product_name }}</strong>!</p>
  <p><a href="{{ product_url }}" style="display: inline-block; background: #38a169; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">Shop Now</a></p>
  <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
  <p style="font-size: 12px; color: #718096;">
    <a href="{{ unsubscribe_url }}">Unsubscribe</a>
  </p>
</body>
</html>""",
    },
    "newsletter": {
        "subject": "{{ store_name }} Newsletter",
        "html": """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #2d3748;">{{ store_name }} Newsletter</h1>
  <p>Hi {{ first_name }},</p>
  <p>Here's what's new at {{ store_name }}.</p>
  <p>Stay tuned for exciting updates, product launches, and exclusive subscriber-only deals.</p>
  <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
  <p style="font-size: 12px; color: #718096;">
    <a href="{{ unsubscribe_url }}">Unsubscribe</a>
  </p>
</body>
</html>""",
    },
}


def _strip_html(html_text: str) -> str:
    """
    Convert HTML to plain text by stripping tags and decoding entities.

    Args:
        html_text: HTML string to convert.

    Returns:
        Plain-text string with tags removed and entities decoded.
    """
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", html_text)
    # Decode HTML entities
    text = html.unescape(text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Preserve paragraph breaks
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text


def render_html(html_content: str, variables: dict[str, str] | None = None) -> str:
    """
    Render an arbitrary HTML string with Jinja2 variable substitution.

    Missing variables render as empty strings (no errors raised).

    Args:
        html_content: HTML string containing ``{{ variable }}`` placeholders.
        variables: Dict of variable names to values.

    Returns:
        Rendered HTML string with variables replaced.
    """
    template = _env.from_string(html_content)
    return template.render(**(variables or {}))


def render_template(
    template_name: str,
    variables: dict[str, str] | None = None,
) -> tuple[str, str]:
    """
    Render a built-in email template by name.

    Looks up the template in ``BUILTIN_TEMPLATES``, renders the HTML with
    the provided variables, and generates a plain-text fallback by
    stripping HTML tags.

    Args:
        template_name: Name of the built-in template. One of:
            "welcome", "order_confirmation", "shipping_notification",
            "abandoned_cart", "promotional", "newsletter".
        variables: Dict of variable names to substitute. Supported variables:
            - first_name: Recipient's first name.
            - last_name: Recipient's last name.
            - email: Recipient's email address.
            - product_name: Product being referenced.
            - product_url: Link to the product or order.
            - unsubscribe_url: One-click unsubscribe link.
            - store_name: The store/brand name.

    Returns:
        Tuple of (rendered_html, rendered_plain_text).

    Raises:
        ValueError: If template_name is not a recognized built-in template.
    """
    if template_name not in BUILTIN_TEMPLATES:
        available = ", ".join(sorted(BUILTIN_TEMPLATES.keys()))
        raise ValueError(
            f"Unknown template '{template_name}'. Available: {available}"
        )

    template_data = BUILTIN_TEMPLATES[template_name]
    rendered_html = render_html(template_data["html"], variables)
    plain_text = _strip_html(rendered_html)

    return rendered_html, plain_text


def render_subject(
    template_name: str,
    variables: dict[str, str] | None = None,
) -> str:
    """
    Render the subject line of a built-in template.

    Args:
        template_name: Name of the built-in template.
        variables: Dict of variable names to substitute.

    Returns:
        Rendered subject line string.

    Raises:
        ValueError: If template_name is not a recognized built-in template.
    """
    if template_name not in BUILTIN_TEMPLATES:
        available = ", ".join(sorted(BUILTIN_TEMPLATES.keys()))
        raise ValueError(
            f"Unknown template '{template_name}'. Available: {available}"
        )

    subject_template = BUILTIN_TEMPLATES[template_name]["subject"]
    return render_html(subject_template, variables)


def get_available_templates() -> list[str]:
    """
    List the names of all available built-in templates.

    Returns:
        Sorted list of template name strings.
    """
    return sorted(BUILTIN_TEMPLATES.keys())
