"""
Pipeline execution management API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models import (
    Execution, ExecutionCreate, ExecutionListResponse,
    ExecutionStatus, ApiResponse
)
from app.database import db
from app.pipeline_engine import engine
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    pipeline_id: Optional[str] = None,
    status: Optional[ExecutionStatus] = None
):
    """List executions with pagination and filtering"""
    try:
        executions = await db.list_executions(
            skip=skip, 
            limit=limit, 
            pipeline_id=pipeline_id, 
            status=status
        )
        
        total = len(await db.list_executions(pipeline_id=pipeline_id, status=status))
        
        return ExecutionListResponse(
            executions=executions,
            total=total,
            page=skip // limit + 1,
            size=len(executions)
        )
        
    except Exception as e:
        logger.error(f"Error listing executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}", response_model=Execution)
async def get_execution(execution_id: str):
    """Get a specific execution by ID"""
    try:
        execution = await db.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return execution
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/executions/{execution_id}/cancel", response_model=ApiResponse)
async def cancel_execution(execution_id: str):
    """Cancel a running execution"""
    try:
        # Check if execution exists
        execution = await db.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel execution with status: {execution.status}"
            )
        
        # Cancel execution
        success = await engine.cancel_execution(execution_id)
        if not success:
            raise HTTPException(status_code=400, detail="Execution not found or not running")
        
        logger.info(f"Cancelled execution: {execution_id}")
        return ApiResponse(success=True, message="Execution cancelled successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}/logs")
async def get_execution_logs(execution_id: str):
    """Get execution logs"""
    try:
        execution = await db.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return {
            "execution_id": execution_id,
            "logs": execution.logs,
            "total_logs": len(execution.logs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution logs {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}/steps")
async def get_execution_steps(execution_id: str):
    """Get execution step details"""
    try:
        execution = await db.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return {
            "execution_id": execution_id,
            "steps": execution.steps,
            "total_steps": len(execution.steps)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution steps {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}/progress")
async def get_execution_progress(execution_id: str):
    """Get execution progress information"""
    try:
        execution = await db.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        total_steps = len(execution.steps)
        completed_steps = len([s for s in execution.steps if s.status == ExecutionStatus.COMPLETED])
        failed_steps = len([s for s in execution.steps if s.status == ExecutionStatus.FAILED])
        running_steps = len([s for s in execution.steps if s.status == ExecutionStatus.RUNNING])
        
        progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        return {
            "execution_id": execution_id,
            "status": execution.status,
            "progress_percentage": round(progress_percentage, 2),
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "running_steps": running_steps,
            "start_time": execution.start_time.isoformat() if execution.start_time else None,
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "duration": execution.duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution progress {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/running")
async def get_running_executions():
    """Get list of currently running executions"""
    try:
        running_execution_ids = await engine.get_running_executions()
        
        running_executions = []
        for execution_id in running_execution_ids:
            execution = await db.get_execution(execution_id)
            if execution:
                running_executions.append(execution)
        
        return {
            "running_executions": running_executions,
            "count": len(running_executions)
        }
        
    except Exception as e:
        logger.error(f"Error getting running executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_execution_statistics():
    """Get execution statistics"""
    try:
        # Get all executions for statistics
        all_executions = await db.list_executions(limit=10000)  # Large limit to get all
        
        total_executions = len(all_executions)
        
        # Count by status
        status_counts = {}
        for status in ExecutionStatus:
            status_counts[status.value] = len([e for e in all_executions if e.status == status])
        
        # Calculate success rate
        completed = status_counts.get(ExecutionStatus.COMPLETED.value, 0)
        failed = status_counts.get(ExecutionStatus.FAILED.value, 0)
        success_rate = (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0
        
        # Average execution time for completed executions
        total_duration = 0.0
        completed_count = 0
        for execution in all_executions:
            if execution.status == ExecutionStatus.COMPLETED and execution.duration:
                total_duration += execution.duration
                completed_count += 1
        
        avg_duration = total_duration / completed_count if completed_count > 0 else 0
        
        # Recent activity (last 24 hours)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_executions = [e for e in all_executions if e.created_at >= recent_cutoff]
        
        return {
            "total_executions": total_executions,
            "status_counts": status_counts,
            "success_rate": round(success_rate, 2),
            "average_duration": round(avg_duration, 2),
            "recent_executions_24h": len(recent_executions)
        }
        
    except Exception as e:
        logger.error(f"Error getting execution statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
