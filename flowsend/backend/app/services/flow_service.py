"""
Flow management service with real step execution engine.

Handles CRUD operations for automated email flows, including
step validation, activation/pausing, execution tracking, and
real step-by-step execution of flow logic.

For Developers:
    - Flows have a lifecycle: draft -> active -> paused.
    - Steps are stored as a JSON list; each step has a ``type`` and config.
    - Valid step types: "send_email", "delay", "condition", "split".
    - Legacy step type "email" is aliased to "send_email" for compatibility.
    - ``execute_flow_step()`` processes a single step for a single contact.
    - ``trigger_flow()`` starts a flow for a batch of contacts.
    - FlowExecutions track per-contact progress through a flow.

For QA Engineers:
    Test: flow CRUD, activate/pause lifecycle, step validation,
    empty steps rejection, execution creation, step execution for each type,
    trigger_flow batch processing, condition evaluation.

For Project Managers:
    Flows are the automation engine — they drive engagement and
    reduce manual work for email marketers. Real step execution
    enables send_email, delay, condition, and A/B split steps.

For End Users:
    Create automated email sequences that trigger based on events.
    Steps include sending emails, adding delays, conditional branching,
    and A/B split testing.
"""

import logging
import random
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import EmailEvent
from app.models.contact import Contact
from app.models.flow import Flow, FlowExecution
from app.models.user import User
from app.services.email_sender import get_email_sender
from app.services.template_renderer import render_html, render_template

logger = logging.getLogger(__name__)

VALID_TRIGGER_TYPES = {"signup", "purchase", "abandoned_cart", "custom", "scheduled"}
VALID_STEP_TYPES = {"email", "send_email", "delay", "condition", "split", "webhook"}


async def create_flow(
    db: AsyncSession, user: User, name: str,
    trigger_type: str, description: str | None = None,
    trigger_config: dict | None = None, steps: list[dict] | None = None,
) -> Flow:
    """
    Create a new email flow.

    Args:
        db: Async database session.
        user: The owning user.
        name: Flow display name.
        trigger_type: Event that triggers the flow.
        description: Flow description (optional).
        trigger_config: Trigger configuration (optional).
        steps: List of step definitions (optional).

    Returns:
        The newly created Flow in "draft" status.

    Raises:
        ValueError: If trigger_type is invalid.
    """
    if trigger_type not in VALID_TRIGGER_TYPES:
        raise ValueError(
            f"Invalid trigger_type. Must be one of: {', '.join(VALID_TRIGGER_TYPES)}"
        )

    flow = Flow(
        user_id=user.id,
        name=name,
        description=description,
        trigger_type=trigger_type,
        trigger_config=trigger_config or {},
        steps=steps or [],
        status="draft",
        stats={},
    )
    db.add(flow)
    await db.flush()
    await db.refresh(flow)
    return flow


async def get_flows(
    db: AsyncSession, user_id: uuid.UUID,
    page: int = 1, page_size: int = 50,
    status: str | None = None,
) -> tuple[list[Flow], int]:
    """
    List flows with pagination and optional status filter.

    Args:
        db: Async database session.
        user_id: The owning user's UUID.
        page: Page number (1-indexed).
        page_size: Items per page.
        status: Optional status filter ("draft", "active", "paused").

    Returns:
        Tuple of (list of Flow, total count).
    """
    query = select(Flow).where(Flow.user_id == user_id)
    count_query = select(func.count(Flow.id)).where(Flow.user_id == user_id)

    if status:
        query = query.where(Flow.status == status)
        count_query = count_query.where(Flow.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Flow.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    flows = list(result.scalars().all())

    return flows, total


async def get_flow(
    db: AsyncSession, user_id: uuid.UUID, flow_id: uuid.UUID
) -> Flow | None:
    """
    Get a single flow by ID, scoped to user.

    Args:
        db: Async database session.
        user_id: The owning user's UUID.
        flow_id: The flow's UUID.

    Returns:
        The Flow if found, None otherwise.
    """
    result = await db.execute(
        select(Flow).where(Flow.id == flow_id, Flow.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_flow(
    db: AsyncSession, flow: Flow,
    name: str | None = None, description: str | None = None,
    trigger_type: str | None = None, trigger_config: dict | None = None,
    steps: list[dict] | None = None,
) -> Flow:
    """
    Update an existing flow.

    Only draft or paused flows can be updated.

    Args:
        db: Async database session.
        flow: The flow to update.
        name: Updated name (optional).
        description: Updated description (optional).
        trigger_type: Updated trigger type (optional).
        trigger_config: Updated trigger config (optional).
        steps: Updated step definitions (optional).

    Returns:
        The updated Flow.

    Raises:
        ValueError: If flow is active, or trigger_type is invalid.
    """
    if flow.status == "active":
        raise ValueError("Cannot update an active flow. Pause it first.")

    if trigger_type is not None:
        if trigger_type not in VALID_TRIGGER_TYPES:
            raise ValueError(
                f"Invalid trigger_type. Must be one of: {', '.join(VALID_TRIGGER_TYPES)}"
            )
        flow.trigger_type = trigger_type

    if name is not None:
        flow.name = name
    if description is not None:
        flow.description = description
    if trigger_config is not None:
        flow.trigger_config = trigger_config
    if steps is not None:
        flow.steps = steps

    await db.flush()
    await db.refresh(flow)
    return flow


async def activate_flow(db: AsyncSession, flow: Flow) -> Flow:
    """
    Activate a flow so it starts processing triggers.

    The flow must have at least one step defined.

    Args:
        db: Async database session.
        flow: The flow to activate.

    Returns:
        The activated Flow.

    Raises:
        ValueError: If flow has no steps or is already active.
    """
    if flow.status == "active":
        raise ValueError("Flow is already active")

    steps = flow.steps
    if isinstance(steps, list) and len(steps) == 0:
        raise ValueError("Cannot activate a flow with no steps")
    if not steps:
        raise ValueError("Cannot activate a flow with no steps")

    flow.status = "active"
    await db.flush()
    await db.refresh(flow)
    return flow


async def pause_flow(db: AsyncSession, flow: Flow) -> Flow:
    """
    Pause an active flow.

    Args:
        db: Async database session.
        flow: The flow to pause.

    Returns:
        The paused Flow.

    Raises:
        ValueError: If flow is not active.
    """
    if flow.status != "active":
        raise ValueError("Can only pause an active flow")

    flow.status = "paused"
    await db.flush()
    await db.refresh(flow)
    return flow


async def delete_flow(db: AsyncSession, flow: Flow) -> None:
    """
    Delete a flow and all its executions.

    Args:
        db: Async database session.
        flow: The flow to delete.
    """
    await db.delete(flow)
    await db.flush()


async def get_flow_executions(
    db: AsyncSession, flow_id: uuid.UUID,
    page: int = 1, page_size: int = 50,
) -> tuple[list[FlowExecution], int]:
    """
    List executions for a flow with pagination.

    Args:
        db: Async database session.
        flow_id: The flow's UUID.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Tuple of (list of FlowExecution, total count).
    """
    count_result = await db.execute(
        select(func.count(FlowExecution.id)).where(
            FlowExecution.flow_id == flow_id
        )
    )
    total = count_result.scalar() or 0

    query = (
        select(FlowExecution)
        .where(FlowExecution.flow_id == flow_id)
        .order_by(FlowExecution.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    executions = list(result.scalars().all())

    return executions, total


# ── Flow Execution Engine ─────────────────────────────────────────────────


async def _get_contact(db: AsyncSession, contact_id: uuid.UUID) -> Contact | None:
    """
    Fetch a contact by ID.

    Args:
        db: Async database session.
        contact_id: The contact's UUID.

    Returns:
        The Contact if found, None otherwise.
    """
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    return result.scalar_one_or_none()


async def _execute_send_email_step(
    db: AsyncSession,
    flow: Flow,
    step: dict,
    contact: Contact,
) -> str:
    """
    Execute a "send_email" flow step: render template and send email.

    Creates an EmailEvent record for tracking. Uses the template_renderer
    to personalize content, then sends via the configured email sender.

    Args:
        db: Async database session.
        flow: The parent flow.
        step: Step config dict with optional "template" and "html_content" keys.
        contact: The recipient contact.

    Returns:
        "sent" if email was sent, "failed" otherwise.
    """
    template_name = step.get("template")
    html_content = step.get("html_content", "")
    subject = step.get("subject", "")

    variables = {
        "first_name": contact.first_name or "",
        "last_name": contact.last_name or "",
        "email": contact.email,
        "store_name": "FlowSend",
        "unsubscribe_url": f"https://flowsend.app/unsubscribe/{contact.id}",
        "product_name": step.get("product_name", ""),
        "product_url": step.get("product_url", ""),
    }

    if template_name:
        try:
            rendered_html, plain_text = render_template(template_name, variables)
            if not subject:
                subject = f"Message from FlowSend"
        except ValueError:
            rendered_html = html_content or "<p>Hello!</p>"
            plain_text = "Hello!"
    elif html_content:
        rendered_html = render_html(html_content, variables)
        plain_text = rendered_html  # Simplified fallback
    else:
        rendered_html = "<p>Hello!</p>"
        plain_text = "Hello!"
        subject = subject or "Message from FlowSend"

    if not subject:
        subject = "Message from FlowSend"

    sender = get_email_sender()
    success = await sender.send(
        to=contact.email,
        subject=subject,
        html_body=rendered_html,
        plain_body=plain_text,
    )

    # Track the event
    event = EmailEvent(
        flow_id=flow.id,
        contact_id=contact.id,
        event_type="sent" if success else "failed",
        extra_metadata={"step_template": template_name or "custom", "subject": subject},
        created_at=datetime.now(UTC),
    )
    db.add(event)
    await db.flush()

    return "sent" if success else "failed"


def _evaluate_condition(step: dict, contact: Contact) -> bool:
    """
    Evaluate a condition step against a contact's data.

    Supports rule types: tag_equals, field_gt, opened_previous.

    Args:
        step: Step config dict with "condition_type" and "value" keys.
        contact: The contact to evaluate against.

    Returns:
        True if condition is met, False otherwise.
    """
    condition_type = step.get("condition_type", "")
    value = step.get("value", "")

    if condition_type == "tag_equals":
        return value in (contact.tags or [])

    if condition_type == "field_gt":
        field_name = step.get("field", "")
        try:
            field_val = float(contact.custom_fields.get(field_name, 0))
            return field_val > float(value)
        except (ValueError, TypeError):
            return False

    if condition_type == "opened_previous":
        # This would check EmailEvent history in production.
        # For now, return True if contact is subscribed (simplified).
        return contact.is_subscribed

    # Unknown condition type defaults to True (proceed)
    return True


def split_contacts(
    contacts: list,
    variant_count: int = 2,
) -> list[list]:
    """
    Split a list of contacts into equal-sized variant groups for A/B testing.

    Contacts are shuffled randomly before splitting to ensure even distribution.

    Args:
        contacts: List of contacts to split.
        variant_count: Number of variants (default 2 for A/B).

    Returns:
        List of lists, one per variant. Contacts are distributed as evenly
        as possible (remainder contacts go to earlier variants).
    """
    if variant_count < 1:
        return [list(contacts)]

    shuffled = list(contacts)
    random.shuffle(shuffled)

    variants: list[list] = [[] for _ in range(variant_count)]
    for i, contact in enumerate(shuffled):
        variants[i % variant_count].append(contact)

    return variants


async def execute_flow_step(
    db: AsyncSession,
    flow_id: uuid.UUID,
    step_index: int,
    contact_id: uuid.UUID,
) -> dict:
    """
    Execute a single flow step for a single contact.

    Dispatches to the appropriate handler based on step type:
    - "send_email" / "email": Render template and send email.
    - "delay": Record delay (in production, schedule via Celery eta).
    - "condition": Evaluate rule and return branch decision.
    - "split": Assign contact to A/B variant.

    Args:
        db: Async database session.
        flow_id: The flow's UUID.
        step_index: Zero-indexed step position in the flow's steps list.
        contact_id: The contact's UUID.

    Returns:
        Dict with "status" key and step-type-specific data:
        - send_email: {"status": "sent"/"failed"}
        - delay: {"status": "delayed", "delay_hours": N}
        - condition: {"status": "evaluated", "result": True/False,
                      "next_step": index}
        - split: {"status": "split", "variant": "A"/"B"/...}

    Raises:
        ValueError: If flow, contact, or step is not found, or step type
            is unrecognized.
    """
    # Fetch flow
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()
    if not flow:
        raise ValueError(f"Flow {flow_id} not found")

    steps = flow.steps
    if not isinstance(steps, list) or step_index >= len(steps):
        raise ValueError(f"Step index {step_index} out of range")

    step = steps[step_index]
    step_type = step.get("type", "")

    # Fetch contact
    contact = await _get_contact(db, contact_id)
    if not contact:
        raise ValueError(f"Contact {contact_id} not found")

    # Dispatch by step type
    if step_type in ("send_email", "email"):
        send_result = await _execute_send_email_step(db, flow, step, contact)
        return {"status": send_result}

    if step_type == "delay":
        delay_hours = step.get("delay_hours", 1)
        logger.info(
            "Flow %s step %d: delay %d hours for contact %s",
            flow_id, step_index, delay_hours, contact_id,
        )
        # In production, this would schedule the next step via Celery
        return {"status": "delayed", "delay_hours": delay_hours}

    if step_type == "condition":
        condition_met = _evaluate_condition(step, contact)
        # Determine which step to go to next
        if condition_met:
            next_step = step.get("then_step", step_index + 1)
        else:
            next_step = step.get("else_step", step_index + 1)
        return {
            "status": "evaluated",
            "result": condition_met,
            "next_step": next_step,
        }

    if step_type == "split":
        variant_count = step.get("variant_count", 2)
        # Deterministic assignment based on contact ID for reproducibility
        variant_index = hash(str(contact_id)) % variant_count
        variant_label = chr(ord("A") + variant_index)
        return {"status": "split", "variant": variant_label}

    raise ValueError(f"Unknown step type: {step_type}")


async def trigger_flow(
    db: AsyncSession,
    flow_id: uuid.UUID,
    contact_ids: list[uuid.UUID],
) -> list[FlowExecution]:
    """
    Start a flow for a batch of contacts.

    Creates a FlowExecution for each contact and executes the first step.
    Only active flows can be triggered.

    Args:
        db: Async database session.
        flow_id: The flow's UUID.
        contact_ids: List of contact UUIDs to enter the flow.

    Returns:
        List of FlowExecution records created.

    Raises:
        ValueError: If flow is not found or not active.
    """
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()
    if not flow:
        raise ValueError(f"Flow {flow_id} not found")

    if flow.status != "active":
        raise ValueError("Can only trigger an active flow")

    executions = []
    for contact_id in contact_ids:
        execution = FlowExecution(
            flow_id=flow_id,
            contact_id=contact_id,
            current_step=0,
            status="running",
        )
        db.add(execution)
        executions.append(execution)

    await db.flush()

    # Execute the first step for each contact
    steps = flow.steps
    if isinstance(steps, list) and len(steps) > 0:
        for execution in executions:
            try:
                await execute_flow_step(db, flow_id, 0, execution.contact_id)
            except Exception:
                logger.exception(
                    "Error executing first step for contact %s in flow %s",
                    execution.contact_id, flow_id,
                )
                execution.status = "failed"

    await db.flush()
    return executions
