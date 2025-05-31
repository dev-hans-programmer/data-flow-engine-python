"""
Pipeline management API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models import (
    Pipeline, PipelineCreate, PipelineUpdate, PipelineListResponse,
    PipelineStatus, ApiResponse, ErrorResponse
)
from app.database import db
from app.pipeline_engine import engine
from app.scheduler import PipelineScheduler
from app.services.validation import validate_pipeline_config
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Global scheduler reference (will be set from main.py)
scheduler: Optional[PipelineScheduler] = None


@router.post("/pipelines", response_model=Pipeline)
async def create_pipeline(pipeline_data: PipelineCreate):
    """Create a new pipeline"""
    try:
        # Validate pipeline configuration
        validation_result = await validate_pipeline_config(pipeline_data.dict())
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Pipeline validation failed: {validation_result['errors']}"
            )
        
        # Create pipeline object
        pipeline = Pipeline(**pipeline_data.dict())
        
        # Store in database
        created_pipeline = await db.create_pipeline(pipeline)
        
        # Add to scheduler if it has a schedule and is active
        if created_pipeline.schedule and created_pipeline.status == PipelineStatus.ACTIVE and scheduler:
            await scheduler.add_pipeline_schedule(created_pipeline)
        
        logger.info(f"Created pipeline: {created_pipeline.id}")
        return created_pipeline
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipelines", response_model=PipelineListResponse)
async def list_pipelines(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[PipelineStatus] = None
):
    """List pipelines with pagination and filtering"""
    try:
        pipelines = await db.list_pipelines(skip=skip, limit=limit, status=status)
        total = len(await db.list_pipelines(status=status))
        
        return PipelineListResponse(
            pipelines=pipelines,
            total=total,
            page=skip // limit + 1,
            size=len(pipelines)
        )
        
    except Exception as e:
        logger.error(f"Error listing pipelines: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipelines/{pipeline_id}", response_model=Pipeline)
async def get_pipeline(pipeline_id: str):
    """Get a specific pipeline by ID"""
    try:
        pipeline = await db.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        return pipeline
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/pipelines/{pipeline_id}", response_model=Pipeline)
async def update_pipeline(pipeline_id: str, pipeline_update: PipelineUpdate):
    """Update an existing pipeline"""
    try:
        # Get existing pipeline
        existing_pipeline = await db.get_pipeline(pipeline_id)
        if not existing_pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        # Update pipeline data
        update_data = pipeline_update.dict(exclude_unset=True)
        
        # Validate if steps are being updated
        if "steps" in update_data:
            validation_result = await validate_pipeline_config(update_data)
            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Pipeline validation failed: {validation_result['errors']}"
                )
        
        # Apply updates
        for field, value in update_data.items():
            setattr(existing_pipeline, field, value)
        
        # Update in database
        updated_pipeline = await db.update_pipeline(pipeline_id, existing_pipeline)
        if not updated_pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        # Update scheduler if schedule changed
        if scheduler:
            if updated_pipeline.schedule and updated_pipeline.status == PipelineStatus.ACTIVE:
                await scheduler.update_pipeline_schedule(updated_pipeline)
            else:
                await scheduler.remove_pipeline_schedule(pipeline_id)
        
        logger.info(f"Updated pipeline: {pipeline_id}")
        return updated_pipeline
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pipelines/{pipeline_id}", response_model=ApiResponse)
async def delete_pipeline(pipeline_id: str):
    """Delete a pipeline"""
    try:
        # Check if pipeline exists
        pipeline = await db.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        # Remove from scheduler
        if scheduler:
            await scheduler.remove_pipeline_schedule(pipeline_id)
        
        # Delete from database
        success = await db.delete_pipeline(pipeline_id)
        if not success:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        logger.info(f"Deleted pipeline: {pipeline_id}")
        return ApiResponse(success=True, message="Pipeline deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipelines/{pipeline_id}/execute")
async def execute_pipeline(pipeline_id: str, parameters: dict = None):
    """Execute a pipeline"""
    try:
        # Get pipeline
        pipeline = await db.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        if pipeline.status != PipelineStatus.ACTIVE:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot execute pipeline with status: {pipeline.status}"
            )
        
        # Execute pipeline
        execution = await engine.execute_pipeline(pipeline, parameters or {})
        
        logger.info(f"Started execution: {execution.id} for pipeline: {pipeline_id}")
        return execution
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipelines/{pipeline_id}/validate", response_model=ApiResponse)
async def validate_pipeline(pipeline_id: str):
    """Validate a pipeline configuration"""
    try:
        # Get pipeline
        pipeline = await db.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        # Validate pipeline
        validation_result = await validate_pipeline_config(pipeline.dict())
        
        return ApiResponse(
            success=validation_result["valid"],
            message="Pipeline validation completed",
            data=validation_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipelines/{pipeline_id}/schedule")
async def get_pipeline_schedule(pipeline_id: str):
    """Get pipeline schedule information"""
    try:
        pipeline = await db.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        schedule_info = {
            "pipeline_id": pipeline_id,
            "schedule": pipeline.schedule.dict() if pipeline.schedule else None,
            "scheduled": pipeline.schedule is not None,
            "next_run": None,
            "enabled": False
        }
        
        # Get scheduler info if available
        if scheduler and pipeline_id in scheduler.jobs:
            job = scheduler.jobs[pipeline_id]
            schedule_info.update({
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "enabled": job.enabled,
                "last_run": job.last_run.isoformat() if job.last_run else None
            })
        
        return schedule_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pipeline schedule {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipelines/{pipeline_id}/schedule/enable", response_model=ApiResponse)
async def enable_pipeline_schedule(pipeline_id: str):
    """Enable pipeline schedule"""
    try:
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")
        
        await scheduler.enable_job(pipeline_id)
        return ApiResponse(success=True, message="Pipeline schedule enabled")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling pipeline schedule {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipelines/{pipeline_id}/schedule/disable", response_model=ApiResponse)
async def disable_pipeline_schedule(pipeline_id: str):
    """Disable pipeline schedule"""
    try:
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")
        
        await scheduler.disable_job(pipeline_id)
        return ApiResponse(success=True, message="Pipeline schedule disabled")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling pipeline schedule {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Set scheduler reference (called from main.py)
def set_scheduler(scheduler_instance: PipelineScheduler):
    global scheduler
    scheduler = scheduler_instance
