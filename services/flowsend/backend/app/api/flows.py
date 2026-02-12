"""
Flow management API endpoints.

Provides CRUD for automated email flows, plus activate/pause lifecycle
management and execution listing.

For Developers:
    Flows have a draft -> active -> paused lifecycle. Active flows
    cannot be edited (must be paused first). Activation requires
    at least one step defined.

For QA Engineers:
    Test: create, list, get, update (draft only), delete, activate
    (with steps), activate (empty steps fails), pause, list executions.

For Project Managers:
    Flows are the core automation feature. They reduce manual work
    and improve engagement through timely automated emails.

For End Users:
    Create email sequences that trigger automatically based on
    events like new signups or purchases.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.email import (
    FlowCreate,
    FlowExecutionResponse,
    FlowResponse,
    FlowUpdate,
    PaginatedResponse,
)
from app.services.flow_service import (
    activate_flow,
    create_flow,
    delete_flow,
    get_flow,
    get_flow_executions,
    get_flows,
    pause_flow,
    update_flow,
)

router = APIRouter(prefix="/flows", tags=["flows"])


@router.post("", response_model=FlowResponse, status_code=201)
async def create_flow_endpoint(
    body: FlowCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new email flow.

    Creates in "draft" status. Add steps and then activate.

    Args:
        body: Flow creation data (name, trigger_type, trigger_config, steps).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created flow.

    Raises:
        HTTPException 400: If trigger_type is invalid.
    """
    try:
        flow = await create_flow(
            db, current_user, body.name,
            trigger_type=body.trigger_type,
            description=body.description,
            trigger_config=body.trigger_config,
            steps=body.steps,
        )
        return flow
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=PaginatedResponse[FlowResponse])
async def list_flows(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    flow_status: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List flows with pagination and optional status filter.

    Args:
        page: Page number.
        page_size: Items per page.
        flow_status: Optional status filter (draft, active, paused).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of flows.
    """
    flows, total = await get_flows(
        db, current_user.id, page=page, page_size=page_size,
        status=flow_status,
    )
    return PaginatedResponse(
        items=flows, total=total, page=page, page_size=page_size
    )


@router.get("/{flow_id}", response_model=FlowResponse)
async def get_flow_endpoint(
    flow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single flow by ID.

    Args:
        flow_id: The flow's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The flow data.

    Raises:
        HTTPException 404: If flow not found.
    """
    flow = await get_flow(db, current_user.id, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow


@router.patch("/{flow_id}", response_model=FlowResponse)
async def update_flow_endpoint(
    flow_id: uuid.UUID,
    body: FlowUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a flow (draft or paused only).

    Active flows must be paused before updating.

    Args:
        flow_id: The flow's UUID.
        body: Update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated flow.

    Raises:
        HTTPException 404: If flow not found.
        HTTPException 400: If flow is active or trigger_type is invalid.
    """
    flow = await get_flow(db, current_user.id, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    try:
        updated = await update_flow(
            db, flow,
            name=body.name, description=body.description,
            trigger_type=body.trigger_type, trigger_config=body.trigger_config,
            steps=body.steps,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{flow_id}", status_code=204)
async def delete_flow_endpoint(
    flow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a flow and all its executions.

    Args:
        flow_id: The flow's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If flow not found.
    """
    flow = await get_flow(db, current_user.id, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    await delete_flow(db, flow)


@router.post("/{flow_id}/activate", response_model=FlowResponse)
async def activate_flow_endpoint(
    flow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Activate a flow to start processing triggers.

    Flow must have at least one step defined.

    Args:
        flow_id: The flow's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The activated flow.

    Raises:
        HTTPException 404: If flow not found.
        HTTPException 400: If flow has no steps or is already active.
    """
    flow = await get_flow(db, current_user.id, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    try:
        activated = await activate_flow(db, flow)
        return activated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{flow_id}/pause", response_model=FlowResponse)
async def pause_flow_endpoint(
    flow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pause an active flow.

    Args:
        flow_id: The flow's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The paused flow.

    Raises:
        HTTPException 404: If flow not found.
        HTTPException 400: If flow is not active.
    """
    flow = await get_flow(db, current_user.id, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    try:
        paused = await pause_flow(db, flow)
        return paused
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{flow_id}/executions", response_model=PaginatedResponse[FlowExecutionResponse])
async def list_flow_executions(
    flow_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List executions for a flow with pagination.

    Args:
        flow_id: The flow's UUID.
        page: Page number.
        page_size: Items per page.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of flow executions.

    Raises:
        HTTPException 404: If flow not found.
    """
    flow = await get_flow(db, current_user.id, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    executions, total = await get_flow_executions(
        db, flow_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=executions, total=total, page=page, page_size=page_size
    )
