"""
Import job API endpoints for SourcePilot.

Handles creation, listing, retrieval, cancellation, retry, and bulk
import of product import jobs. Enforces plan-based import limits.

For Developers:
    All endpoints require JWT authentication via ``get_current_user``.
    The POST /imports endpoint dispatches a Celery task after creating
    the job record. Bulk imports create multiple jobs and dispatch
    individual tasks for each.

For QA Engineers:
    Test: create import (success + plan limit), list imports (pagination
    + filters), get import details, cancel import, retry failed import,
    bulk import. Verify unauthenticated access returns 401.

For Project Managers:
    These endpoints power the Import page in the dashboard.
    Creating an import initiates the product import pipeline.

For End Users:
    Import products from suppliers by providing a product URL.
    View import history, cancel pending imports, and retry failures.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.import_job import ImportJobStatus
from app.models.import_history import ImportHistory
from app.models.user import User
from app.schemas.imports import (
    BulkImportCreate,
    ImportJobCreate,
    ImportJobList,
    ImportJobResponse,
)
from app.services.import_service import (
    cancel_import_job,
    check_import_limit,
    create_bulk_import,
    create_import_job,
    get_import_job,
    list_import_jobs,
    update_import_job_status,
)

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("", response_model=ImportJobResponse, status_code=201)
async def create_import(
    body: ImportJobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new import job and dispatch it for background processing.

    Validates plan limits before creation. The job starts in 'pending'
    status and transitions through the lifecycle as the Celery task executes.

    Args:
        body: Import job creation data (source_url, source, store_id, config).
        current_user: The authenticated user (injected via dependency).
        db: Database session.

    Returns:
        ImportJobResponse with the new job in 'pending' status.

    Raises:
        HTTPException 403: If the user has exceeded their plan's import limit.
        HTTPException 400: If the source type is invalid.
    """
    # Check plan limits
    can_import = await check_import_limit(db, current_user)
    if not can_import:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Import limit reached for {current_user.plan.value} plan. "
                   f"Upgrade your plan for more imports.",
        )

    try:
        job = await create_import_job(db, current_user.id, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Dispatch Celery task for background processing
    try:
        from app.tasks.import_tasks import process_import_job

        process_import_job.delay(str(job.id))
    except Exception:
        # If Celery is unavailable, job still exists in 'pending' state
        pass

    return job


@router.get("")
async def list_imports(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    store_id: uuid.UUID | None = Query(None, description="Filter by store ID"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List the authenticated user's import jobs with pagination and filters.

    Returns jobs ordered by creation date (newest first).
    Supports optional filtering by store_id and status.

    Args:
        skip: Number of items to skip (default 0).
        limit: Max items to return (1-100, default 20).
        store_id: Optional store ID filter.
        status_filter: Optional status filter (pending, running, completed, failed, cancelled).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Dict with items list and total count.
    """
    jobs, total = await list_import_jobs(
        db,
        user_id=current_user.id,
        store_id=store_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return {
        "items": [ImportJobResponse.model_validate(j) for j in jobs],
        "total": total,
    }


@router.get("/{job_id}", response_model=ImportJobResponse)
async def get_import_detail(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific import job.

    Only the owning user can access their import jobs.

    Args:
        job_id: The import job's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ImportJobResponse with full job details.

    Raises:
        HTTPException 404: If job not found or not owned by user.
    """
    job = await get_import_job(db, job_id, current_user.id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        )
    return job


@router.post("/bulk", response_model=list[ImportJobResponse], status_code=201)
async def bulk_import(
    body: BulkImportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create multiple import jobs from a list of product URLs.

    Each URL becomes a separate import job, all sharing the same source,
    store, and configuration. Individual Celery tasks are dispatched for each.

    Args:
        body: Bulk import data (urls, source, store_id, config).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of ImportJobResponse for all created jobs.

    Raises:
        HTTPException 403: If importing all URLs would exceed plan limits.
        HTTPException 400: If the source type is invalid.
    """
    # Check plan limits for all URLs
    can_import = await check_import_limit(db, current_user)
    if not can_import:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Import limit reached for {current_user.plan.value} plan. "
                   f"Upgrade your plan for more imports.",
        )

    try:
        jobs = await create_bulk_import(db, current_user.id, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Dispatch Celery tasks for each job
    try:
        from app.tasks.import_tasks import process_import_job

        for job in jobs:
            process_import_job.delay(str(job.id))
    except Exception:
        pass

    return jobs


@router.post("/{job_id}/cancel", response_model=ImportJobResponse)
async def cancel_import(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a pending or running import job.

    Only jobs in 'pending' or 'running' status can be cancelled.

    Args:
        job_id: The import job's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ImportJobResponse with updated 'cancelled' status.

    Raises:
        HTTPException 404: If job not found or not owned by user.
        HTTPException 400: If the job cannot be cancelled.
    """
    try:
        job = await cancel_import_job(db, job_id, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        )

    return job


@router.post("/{job_id}/retry", response_model=ImportJobResponse)
async def retry_import(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retry a failed import job.

    Resets the job status to 'pending' and dispatches a new Celery task.
    Only jobs in 'failed' or 'cancelled' status can be retried.

    Args:
        job_id: The import job's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ImportJobResponse with reset 'pending' status.

    Raises:
        HTTPException 404: If job not found or not owned by user.
        HTTPException 400: If the job is not in a retryable status.
    """
    job = await get_import_job(db, job_id, current_user.id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        )

    retryable_statuses = {ImportJobStatus.failed, ImportJobStatus.cancelled}
    if job.status not in retryable_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry job in '{job.status.value}' status. "
                   f"Only failed or cancelled jobs can be retried.",
        )

    # Reset job for retry
    updated_job = await update_import_job_status(
        db,
        job_id=job.id,
        status=ImportJobStatus.pending,
        error_message=None,
        progress=0,
    )

    # Create history entry
    history = ImportHistory(
        user_id=current_user.id,
        import_job_id=job.id,
        action="retried",
        details={"previous_status": job.status.value},
    )
    db.add(history)
    await db.flush()

    # Dispatch new Celery task
    try:
        from app.tasks.import_tasks import process_import_job

        process_import_job.delay(str(job.id))
    except Exception:
        pass

    return updated_job
