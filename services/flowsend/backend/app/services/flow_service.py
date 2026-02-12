"""
Flow management service.

Handles CRUD operations for automated email flows, including
step validation, activation/pausing, and execution tracking.

For Developers:
    - Flows have a lifecycle: draft -> active -> paused.
    - Steps are stored as a JSON list; each step has a `type` and `config`.
    - Valid step types: "email", "delay", "condition", "webhook".
    - `activate_flow` validates that the flow has at least one step.
    - FlowExecutions are created per-contact when they enter a flow.

For QA Engineers:
    Test: flow CRUD, activate/pause lifecycle, step validation,
    empty steps rejection, execution creation, status filtering.

For Project Managers:
    Flows are the automation engine — they drive engagement and
    reduce manual work for email marketers.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flow import Flow, FlowExecution
from app.models.user import User


VALID_TRIGGER_TYPES = {"signup", "purchase", "abandoned_cart", "custom", "scheduled"}
VALID_STEP_TYPES = {"email", "delay", "condition", "webhook"}


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
