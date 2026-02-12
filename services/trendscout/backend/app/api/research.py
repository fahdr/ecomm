"""
Research API endpoints for TrendScout.

Handles creation, listing, retrieval, and deletion of research runs
and their results. Enforces plan-based run limits.

For Developers:
    All endpoints require JWT authentication via `get_current_user`.
    The POST /runs endpoint dispatches a Celery task after creating
    the run record. Results are fetched via the run detail endpoint.

For QA Engineers:
    Test: create run (success + plan limit), list runs (pagination),
    get run details (includes results), delete run (cascading).
    Verify unauthenticated access returns 401.

For Project Managers:
    These endpoints power the Research page in the dashboard.
    Creating a run initiates the product-research pipeline.

For End Users:
    Start a research run by POSTing keywords and sources.
    View your run history and results via GET endpoints.
    Delete old runs to keep your history clean.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.research import (
    ResearchResultResponse,
    ResearchRunCreate,
    ResearchRunListResponse,
    ResearchRunResponse,
)
from app.services.research_service import (
    create_research_run,
    delete_research_run,
    get_research_run,
    get_research_runs,
    get_result,
)

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/runs", response_model=ResearchRunResponse, status_code=201)
async def create_run(
    body: ResearchRunCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new research run and dispatch it for background processing.

    Validates plan limits (free = 5 runs/month, pro = 50, enterprise = unlimited).
    The run starts in 'pending' status and transitions to 'running' -> 'completed'
    as the Celery task executes.

    Args:
        body: Research run creation data (keywords, sources, score_config).
        current_user: The authenticated user (injected via dependency).
        db: Database session.

    Returns:
        ResearchRunResponse with the new run in 'pending' status.

    Raises:
        HTTPException 403: If the user has exceeded their plan's run limit.
    """
    try:
        run = await create_research_run(
            db,
            user=current_user,
            keywords=body.keywords,
            sources=body.sources,
            score_config=body.score_config,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    # Dispatch Celery task for background processing
    try:
        from app.tasks.research_tasks import run_research

        run_research.delay(str(run.id))
    except Exception:
        # If Celery is unavailable, run still exists in 'pending' state
        pass

    return run


@router.get("/runs", response_model=ResearchRunListResponse)
async def list_runs(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List the authenticated user's research runs with pagination.

    Returns runs ordered by creation date (newest first).
    Does not include inline results — use GET /runs/{id} for full details.

    Args:
        page: Page number (1-indexed, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ResearchRunListResponse with paginated run list.
    """
    runs, total = await get_research_runs(db, current_user.id, page, per_page)
    return ResearchRunListResponse(
        items=[ResearchRunResponse.model_validate(r) for r in runs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/runs/{run_id}", response_model=ResearchRunResponse)
async def get_run_detail(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific research run.

    Includes all results inline, eagerly loaded with the run.
    Only the owning user can access their runs.

    Args:
        run_id: The research run's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ResearchRunResponse with all results included.

    Raises:
        HTTPException 404: If run not found or not owned by user.
    """
    run = await get_research_run(db, run_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research run not found",
        )
    return run


@router.delete("/runs/{run_id}", status_code=204)
async def delete_run(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a research run and all its results.

    Only the owning user can delete their runs. Results are cascade-deleted.
    Related watchlist items referencing these results are also removed.

    Args:
        run_id: The research run's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If run not found or not owned by user.
    """
    deleted = await delete_research_run(db, run_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research run not found",
        )


@router.get("/results/{result_id}", response_model=ResearchResultResponse)
async def get_result_detail(
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a single research result.

    Only results from the user's own runs can be accessed.

    Args:
        result_id: The research result's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ResearchResultResponse with full result data.

    Raises:
        HTTPException 404: If result not found or not owned by user.
    """
    result = await get_result(db, result_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research result not found",
        )

    # Verify ownership via the parent run
    run = await get_research_run(db, result.run_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research result not found",
        )

    return result
