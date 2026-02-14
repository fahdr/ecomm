"""
Import service for managing product import job lifecycle.

Handles CRUD operations for import jobs, including creation, listing,
status updates, cancellation, bulk creation, and plan limit enforcement.

For Developers:
    All functions accept an AsyncSession and operate within the caller's
    transaction. Use ``await db.flush()`` after mutations to get IDs
    without committing. The ``check_import_limit`` function counts jobs
    in the current billing period and compares against the plan's max_items.

For Project Managers:
    This service is the core business logic for product imports.
    It enforces plan limits and manages job lifecycle.

For QA Engineers:
    Test plan limit enforcement by creating imports up to the limit and
    verifying the next attempt is rejected. Test bulk import with
    various URL counts. Test cancellation of running jobs.

For End Users:
    The import service handles all product import operations: creating
    jobs, tracking progress, retrying failures, and bulk imports.
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PLAN_LIMITS
from app.models.import_history import ImportHistory
from app.models.import_job import ImportJob, ImportJobStatus, ImportSource
from app.models.user import User
from app.schemas.imports import BulkImportCreate, ImportJobCreate
from app.utils.helpers import get_current_billing_period

logger = logging.getLogger(__name__)

# Valid import source values for validation
VALID_SOURCES = {s.value for s in ImportSource}


async def check_import_limit(db: AsyncSession, user: User) -> bool:
    """
    Check whether the user has remaining import quota in the current period.

    Counts import jobs created by this user within the current billing month
    and compares against the plan's max_items limit.

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        True if the user can create another import, False if limit reached.
    """
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_items == -1:
        return True  # Unlimited

    period_start, period_end = get_current_billing_period()
    result = await db.execute(
        select(func.count(ImportJob.id)).where(
            ImportJob.user_id == user.id,
            ImportJob.created_at >= datetime.combine(period_start, datetime.min.time()),
            ImportJob.created_at < datetime.combine(period_end, datetime.min.time()),
        )
    )
    count = result.scalar_one()
    return count < plan_limits.max_items


async def get_import_count_this_period(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Get the number of import jobs created by the user this billing period.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Count of import jobs in the current billing period.
    """
    period_start, period_end = get_current_billing_period()
    result = await db.execute(
        select(func.count(ImportJob.id)).where(
            ImportJob.user_id == user_id,
            ImportJob.created_at >= datetime.combine(period_start, datetime.min.time()),
            ImportJob.created_at < datetime.combine(period_end, datetime.min.time()),
        )
    )
    return result.scalar_one()


async def create_import_job(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: ImportJobCreate,
) -> ImportJob:
    """
    Create a new import job and prepare it for background processing.

    Validates the source type and creates a pending import job. The actual
    import processing happens in the Celery task dispatched by the API route.

    Args:
        db: Async database session.
        user_id: UUID of the user creating the import.
        data: Import job creation data.

    Returns:
        The newly created ImportJob in 'pending' status.

    Raises:
        ValueError: If the source type is invalid.
    """
    if data.source not in VALID_SOURCES:
        raise ValueError(
            f"Invalid source '{data.source}'. Valid sources: {', '.join(sorted(VALID_SOURCES))}"
        )

    job = ImportJob(
        user_id=user_id,
        store_id=data.store_id,
        source=ImportSource(data.source),
        source_url=data.product_url,
        config=data.config,
        status=ImportJobStatus.pending,
        progress_percent=0,
    )
    db.add(job)
    await db.flush()

    # Create history entry
    history = ImportHistory(
        user_id=user_id,
        import_job_id=job.id,
        action="created",
        details={"source_url": data.product_url, "source": data.source},
    )
    db.add(history)
    await db.flush()

    await db.refresh(job)
    return job


async def get_import_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ImportJob | None:
    """
    Get a single import job by ID, scoped to the requesting user.

    Args:
        db: Async database session.
        job_id: The import job's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        The ImportJob if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(ImportJob).where(
            ImportJob.id == job_id,
            ImportJob.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_import_jobs(
    db: AsyncSession,
    user_id: uuid.UUID,
    store_id: uuid.UUID | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[ImportJob], int]:
    """
    Get a paginated list of import jobs for a user with optional filters.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        store_id: Optional store ID filter.
        status: Optional status filter.
        skip: Number of records to skip (offset).
        limit: Maximum number of records to return.

    Returns:
        Tuple of (list of ImportJob, total count).
    """
    base_filter = [ImportJob.user_id == user_id]
    if store_id:
        base_filter.append(ImportJob.store_id == store_id)
    if status:
        base_filter.append(ImportJob.status == ImportJobStatus(status))

    # Count total
    count_result = await db.execute(
        select(func.count(ImportJob.id)).where(*base_filter)
    )
    total = count_result.scalar_one()

    # Fetch page
    result = await db.execute(
        select(ImportJob)
        .where(*base_filter)
        .order_by(ImportJob.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    jobs = list(result.scalars().all())
    return jobs, total


async def update_import_job_status(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: ImportJobStatus,
    error_message: str | None = None,
    created_product_id: uuid.UUID | None = None,
    progress: int | None = None,
) -> ImportJob | None:
    """
    Update the status and related fields of an import job.

    Used primarily by the Celery task to report progress and completion.

    Args:
        db: Async database session.
        job_id: The import job's UUID.
        status: New status value.
        error_message: Error description (for failed status).
        created_product_id: UUID of the created product (for completed status).
        progress: Progress percentage (0-100).

    Returns:
        The updated ImportJob, or None if not found.
    """
    result = await db.execute(
        select(ImportJob).where(ImportJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        return None

    job.status = status
    if error_message is not None:
        job.error_message = error_message
    if created_product_id is not None:
        job.created_product_id = created_product_id
    if progress is not None:
        job.progress_percent = max(0, min(100, progress))

    await db.flush()
    await db.refresh(job)
    return job


async def cancel_import_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ImportJob | None:
    """
    Cancel a pending or running import job.

    Only jobs in 'pending' or 'running' status can be cancelled.
    Completed and failed jobs cannot be cancelled.

    Args:
        db: Async database session.
        job_id: The import job's UUID.
        user_id: The requesting user's UUID (for ownership check).

    Returns:
        The cancelled ImportJob, or None if not found or not cancellable.

    Raises:
        ValueError: If the job is in a non-cancellable status.
    """
    result = await db.execute(
        select(ImportJob).where(
            ImportJob.id == job_id,
            ImportJob.user_id == user_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        return None

    cancellable_statuses = {ImportJobStatus.pending, ImportJobStatus.running}
    if job.status not in cancellable_statuses:
        raise ValueError(
            f"Cannot cancel job in '{job.status.value}' status. "
            f"Only pending or running jobs can be cancelled."
        )

    job.status = ImportJobStatus.cancelled

    # Create history entry
    history = ImportHistory(
        user_id=user_id,
        import_job_id=job.id,
        action="cancelled",
        details={"previous_status": job.status.value},
    )
    db.add(history)

    await db.flush()
    await db.refresh(job)
    return job


async def create_bulk_import(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: BulkImportCreate,
) -> list[ImportJob]:
    """
    Create multiple import jobs from a list of URLs.

    Each URL becomes a separate import job with the same source, store,
    and configuration. All jobs start in 'pending' status.

    Args:
        db: Async database session.
        user_id: UUID of the user creating the imports.
        data: Bulk import creation data with URLs and shared settings.

    Returns:
        List of newly created ImportJob records.

    Raises:
        ValueError: If the source type is invalid.
    """
    if data.source not in VALID_SOURCES:
        raise ValueError(
            f"Invalid source '{data.source}'. Valid sources: {', '.join(sorted(VALID_SOURCES))}"
        )

    jobs = []
    for url in data.product_urls:
        job = ImportJob(
            user_id=user_id,
            store_id=data.store_id,
            source=ImportSource(data.source),
            source_url=url,
            config=data.config,
            status=ImportJobStatus.pending,
            progress_percent=0,
        )
        db.add(job)
        await db.flush()

        # Create history entry for each job
        history = ImportHistory(
            user_id=user_id,
            import_job_id=job.id,
            action="created",
            details={"source_url": url, "source": data.source, "bulk": True},
        )
        db.add(history)
        jobs.append(job)

    await db.flush()

    # Refresh all jobs to load relationships
    for job in jobs:
        await db.refresh(job)

    return jobs
