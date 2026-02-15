"""
Contact segmentation service for dynamic list evaluation.

Evaluates rule-based filters against the contact database to produce
dynamic audience segments. Rules are composable and support a variety
of conditions including tags, custom fields, purchase history, and
engagement metrics.

For Developers:
    - Rules are dicts with ``type`` and ``value`` keys (plus optional extras).
    - Multiple rules are combined with AND logic.
    - Rule types map to SQLAlchemy filter expressions via ``_build_filter()``.
    - To add a new rule type, add a handler in ``_build_filter()`` and
      update ``VALID_RULE_TYPES``.

For QA Engineers:
    Test: each rule type individually, combined rules (AND logic),
    empty rules (return all subscribed contacts), invalid rule types,
    count vs. full evaluation, edge cases (no matching contacts).

For Project Managers:
    Segmentation powers targeted email campaigns. Dynamic lists
    update automatically, so marketers always reach the right audience.

For End Users:
    Create smart segments that automatically include contacts matching
    your criteria (e.g., "VIP tag + purchased in last 30 days").
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import EmailEvent
from app.models.contact import Contact


VALID_RULE_TYPES = {
    "tag_equals",
    "field_gt",
    "field_lt",
    "purchased_product",
    "opened_campaign",
    "clicked_link",
    "subscribed_before",
    "subscribed_after",
}


def _build_filter(rule: dict):
    """
    Convert a segmentation rule dict into a SQLAlchemy filter expression.

    Each rule must have a ``type`` key. Additional keys depend on the rule type.

    Args:
        rule: Dict with at least ``type`` key. Rule-specific keys:
            - tag_equals: ``value`` (str) — tag to match.
            - field_gt: ``field`` (str), ``value`` (numeric) — custom_fields comparison.
            - field_lt: ``field`` (str), ``value`` (numeric) — custom_fields comparison.
            - subscribed_before: ``value`` (ISO date string).
            - subscribed_after: ``value`` (ISO date string).
            - purchased_product / opened_campaign / clicked_link:
              These require subquery-based evaluation and are handled
              separately in ``evaluate_segment()``.

    Returns:
        SQLAlchemy filter expression, or None for subquery-based rules.

    Raises:
        ValueError: If rule type is not recognized.
    """
    rule_type = rule.get("type", "")

    if rule_type not in VALID_RULE_TYPES:
        raise ValueError(
            f"Invalid rule type '{rule_type}'. "
            f"Valid types: {', '.join(sorted(VALID_RULE_TYPES))}"
        )

    if rule_type == "tag_equals":
        tag_value = rule.get("value", "")
        return Contact.tags.any(tag_value)

    if rule_type == "field_gt":
        field_name = rule.get("field", "")
        field_value = rule.get("value", 0)
        return Contact.custom_fields[field_name].as_float() > float(field_value)

    if rule_type == "field_lt":
        field_name = rule.get("field", "")
        field_value = rule.get("value", 0)
        return Contact.custom_fields[field_name].as_float() < float(field_value)

    if rule_type == "subscribed_before":
        date_str = rule.get("value", "")
        cutoff = datetime.fromisoformat(date_str)
        return Contact.subscribed_at < cutoff

    if rule_type == "subscribed_after":
        date_str = rule.get("value", "")
        cutoff = datetime.fromisoformat(date_str)
        return Contact.subscribed_at > cutoff

    # Subquery-based rules return None; handled in evaluate_segment
    return None


async def evaluate_segment(
    db: AsyncSession,
    user_id: uuid.UUID,
    rules: list[dict],
) -> list[Contact]:
    """
    Evaluate segmentation rules and return matching contacts.

    Applies all rules with AND logic. Only subscribed contacts are included.
    Rules that require subqueries (opened_campaign, clicked_link,
    purchased_product) are applied as post-filters on contact IDs.

    Args:
        db: Async database session.
        user_id: The user's UUID (for multi-tenant isolation).
        rules: List of rule dicts. Each must have a ``type`` key.

    Returns:
        List of Contact objects matching all rules.

    Raises:
        ValueError: If any rule type is invalid.
    """
    query = select(Contact).where(
        Contact.user_id == user_id,
        Contact.is_subscribed.is_(True),
    )

    # Collect subquery-based rule types
    subquery_rules = []

    for rule in rules:
        rule_filter = _build_filter(rule)
        if rule_filter is not None:
            query = query.where(rule_filter)
        else:
            subquery_rules.append(rule)

    result = await db.execute(query)
    contacts = list(result.scalars().all())

    # Apply subquery-based filters
    for rule in subquery_rules:
        rule_type = rule.get("type", "")

        if rule_type == "opened_campaign":
            campaign_id = rule.get("value", "")
            event_query = select(EmailEvent.contact_id).where(
                EmailEvent.campaign_id == uuid.UUID(str(campaign_id)),
                EmailEvent.event_type == "opened",
            )
            event_result = await db.execute(event_query)
            opened_ids = {row[0] for row in event_result.all()}
            contacts = [c for c in contacts if c.id in opened_ids]

        elif rule_type == "clicked_link":
            campaign_id = rule.get("value", "")
            event_query = select(EmailEvent.contact_id).where(
                EmailEvent.campaign_id == uuid.UUID(str(campaign_id)),
                EmailEvent.event_type == "clicked",
            )
            event_result = await db.execute(event_query)
            clicked_ids = {row[0] for row in event_result.all()}
            contacts = [c for c in contacts if c.id in clicked_ids]

        elif rule_type == "purchased_product":
            # For purchased_product, we check a "purchased" tag or custom field
            # In a full implementation, this would query the store connection
            product_name = rule.get("value", "")
            contacts = [
                c for c in contacts
                if product_name in c.custom_fields.get("purchased_products", [])
            ]

    return contacts


async def get_segment_count(
    db: AsyncSession,
    user_id: uuid.UUID,
    rules: list[dict],
) -> int:
    """
    Get the count of contacts matching segmentation rules.

    A convenience wrapper around ``evaluate_segment()`` that returns
    only the count instead of full contact objects.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        rules: List of segmentation rule dicts.

    Returns:
        Integer count of matching contacts.
    """
    contacts = await evaluate_segment(db, user_id, rules)
    return len(contacts)
