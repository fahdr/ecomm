"""
Optimization rule management API endpoints.

Handles CRUD operations for automated optimization rules and provides
an execute-now endpoint for manual rule triggering.

For Developers:
    All endpoints require JWT auth. Rules are scoped to the user.
    The execute-now endpoint evaluates the rule against all active
    campaigns and returns the execution result.

For QA Engineers:
    Test: CRUD, execute-now (with and without matching campaigns),
    rule threshold evaluation, execution count increment.

For Project Managers:
    Optimization rules are a premium automation feature. They let
    users set up automated campaign management based on performance.

For End Users:
    Create rules to automatically manage your campaigns. Execute
    rules manually or let them run on schedule.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.ads import (
    PaginatedResponse,
    RuleCreate,
    RuleExecutionResult,
    RuleResponse,
    RuleUpdate,
)
from app.services.optimization_service import (
    create_rule,
    delete_rule,
    evaluate_and_execute,
    get_rule,
    list_rules,
    update_rule,
)

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("", response_model=RuleResponse, status_code=201)
async def create_rule_endpoint(
    request: RuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new optimization rule.

    Args:
        request: Rule creation data (name, type, conditions, threshold).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        RuleResponse with the newly created rule details.
    """
    rule = await create_rule(
        db,
        user_id=current_user.id,
        name=request.name,
        rule_type=request.rule_type,
        conditions=request.conditions,
        threshold=request.threshold,
        is_active=request.is_active,
    )
    return rule


@router.get("", response_model=PaginatedResponse)
async def list_rules_endpoint(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all optimization rules for the current user.

    Args:
        offset: Pagination offset (default 0).
        limit: Maximum items per page (default 50, max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PaginatedResponse with rule items.
    """
    rules, total = await list_rules(db, current_user.id, offset, limit)
    return PaginatedResponse(
        items=[RuleResponse.model_validate(r) for r in rules],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule_endpoint(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific optimization rule by ID.

    Args:
        rule_id: UUID of the rule.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        RuleResponse with rule details.

    Raises:
        HTTPException 404: If rule not found or not owned.
    """
    try:
        rid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")

    rule = await get_rule(db, rid, current_user.id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )
    return rule


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule_endpoint(
    rule_id: str,
    request: RuleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing optimization rule.

    Only provided fields are updated.

    Args:
        rule_id: UUID of the rule to update.
        request: Partial update data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        RuleResponse with updated rule details.

    Raises:
        HTTPException 404: If rule not found or not owned.
    """
    try:
        rid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")

    updates = request.model_dump(exclude_unset=True)
    if "rule_type" in updates and updates["rule_type"] is not None:
        updates["rule_type"] = updates["rule_type"].value

    rule = await update_rule(db, rid, current_user.id, **updates)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule_endpoint(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an optimization rule.

    Args:
        rule_id: UUID of the rule to delete.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If rule not found or not owned.
    """
    try:
        rid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")

    success = await delete_rule(db, rid, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )


@router.post("/{rule_id}/execute", response_model=RuleExecutionResult)
async def execute_rule_endpoint(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute an optimization rule immediately.

    Evaluates the rule against all active campaigns and applies
    the optimization action where thresholds are met.

    Args:
        rule_id: UUID of the rule to execute.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        RuleExecutionResult with campaigns affected and actions taken.

    Raises:
        HTTPException 404: If rule not found or not owned.
    """
    try:
        rid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")

    try:
        result = await evaluate_and_execute(db, rid, current_user.id)
        return RuleExecutionResult(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
