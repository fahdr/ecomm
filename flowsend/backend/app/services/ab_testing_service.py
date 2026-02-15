"""
Campaign A/B testing service for FlowSend.

Enables split testing of email campaigns by dividing contacts into
variant groups, tracking per-variant engagement metrics, and
determining the winning variant based on open rates.

For Developers:
    - ``split_contacts()`` divides contacts into N equal groups.
    - ``track_variant_event()`` records opens/clicks for a variant.
    - ``determine_winner()`` compares open rates across variants.
    - Variant data is stored in the Campaign's JSON fields or EmailEvent metadata.

For QA Engineers:
    Test: even splits (2, 3 variants), uneven splits (odd contact counts),
    single contact, empty list, winner determination with clear winner,
    tied variants, no events (returns first variant).

For Project Managers:
    A/B testing improves campaign performance by letting marketers test
    subject lines, content, and send times. The winning variant can then
    be sent to the remaining audience.

For End Users:
    Test different versions of your email to find what works best.
    FlowSend automatically tracks which version gets more opens and clicks.
"""

import random
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, EmailEvent


def split_contacts_for_ab(
    contacts: list,
    variant_count: int = 2,
) -> list[list]:
    """
    Split a list of contacts into equal-sized groups for A/B testing.

    Contacts are shuffled before splitting to ensure random distribution.
    Remainder contacts are distributed round-robin to earlier variants.

    Args:
        contacts: List of contact objects or IDs to split.
        variant_count: Number of variants to create (default 2 for A/B).

    Returns:
        List of lists, one per variant. Total contacts across all variants
        equals the input list length. Example for 5 contacts, 2 variants:
        [[c1, c3, c5], [c2, c4]].

    Raises:
        ValueError: If variant_count < 1.
    """
    if variant_count < 1:
        raise ValueError("variant_count must be at least 1")

    if not contacts:
        return [[] for _ in range(variant_count)]

    shuffled = list(contacts)
    random.shuffle(shuffled)

    variants: list[list] = [[] for _ in range(variant_count)]
    for i, contact in enumerate(shuffled):
        variants[i % variant_count].append(contact)

    return variants


async def get_variant_stats(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    variant: str,
) -> dict:
    """
    Get engagement statistics for a specific campaign variant.

    Queries EmailEvent records filtered by campaign_id and variant label
    stored in the event's extra_metadata.

    Args:
        db: Async database session.
        campaign_id: The campaign's UUID.
        variant: Variant label (e.g., "A", "B").

    Returns:
        Dict with keys: "variant", "sent", "opened", "clicked".
    """
    base_query = select(func.count(EmailEvent.id)).where(
        EmailEvent.campaign_id == campaign_id,
    )

    # Count sent events for this variant
    sent_result = await db.execute(
        base_query.where(
            EmailEvent.event_type == "sent",
            EmailEvent.extra_metadata["variant"].as_string() == variant,
        )
    )
    sent_count = sent_result.scalar() or 0

    # Count opened events
    opened_result = await db.execute(
        base_query.where(
            EmailEvent.event_type == "opened",
            EmailEvent.extra_metadata["variant"].as_string() == variant,
        )
    )
    opened_count = opened_result.scalar() or 0

    # Count clicked events
    clicked_result = await db.execute(
        base_query.where(
            EmailEvent.event_type == "clicked",
            EmailEvent.extra_metadata["variant"].as_string() == variant,
        )
    )
    clicked_count = clicked_result.scalar() or 0

    return {
        "variant": variant,
        "sent": sent_count,
        "opened": opened_count,
        "clicked": clicked_count,
    }


async def determine_winner(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    variants: list[str] | None = None,
) -> str:
    """
    Determine the winning A/B test variant based on open rate.

    Compares the open rate (opened/sent) across all variants and returns
    the variant label with the highest rate. Ties are broken by the
    variant with more total opens; if still tied, the first variant wins.

    Args:
        db: Async database session.
        campaign_id: The campaign's UUID.
        variants: List of variant labels to compare (default ["A", "B"]).

    Returns:
        The winning variant label string (e.g., "A" or "B").
    """
    if variants is None:
        variants = ["A", "B"]

    best_variant = variants[0]
    best_open_rate = -1.0
    best_opens = 0

    for variant in variants:
        stats = await get_variant_stats(db, campaign_id, variant)

        if stats["sent"] > 0:
            open_rate = stats["opened"] / stats["sent"]
        else:
            open_rate = 0.0

        if (open_rate > best_open_rate) or (
            open_rate == best_open_rate and stats["opened"] > best_opens
        ):
            best_open_rate = open_rate
            best_opens = stats["opened"]
            best_variant = variant

    return best_variant
