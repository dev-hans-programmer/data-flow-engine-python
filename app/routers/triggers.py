"""
API routes for file upload triggers
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from ..services.file_watcher import file_watcher
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

class FileTriggerCreate(BaseModel):
    name: str
    watch_path: str = "uploads"
    pipeline_id: str
    file_patterns: List[str] = ["*"]
    enabled: bool = True

class FileTriggerUpdate(BaseModel):
    name: Optional[str] = None
    watch_path: Optional[str] = None
    pipeline_id: Optional[str] = None
    file_patterns: Optional[List[str]] = None
    enabled: Optional[bool] = None

@router.post("/file-triggers", response_model=Dict[str, str])
async def create_file_trigger(trigger: FileTriggerCreate):
    """Create a new file upload trigger"""
    try:
        trigger_id = await file_watcher.register_file_trigger(trigger.dict())
        return {"trigger_id": trigger_id, "message": "File trigger created successfully"}
        
    except Exception as e:
        logger.error(f"Error creating file trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/file-triggers", response_model=List[Dict[str, Any]])
async def list_file_triggers():
    """List all file upload triggers"""
    try:
        triggers = await file_watcher.list_file_triggers()
        return triggers
    except Exception as e:
        logger.error(f"Error listing file triggers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/file-triggers/{trigger_id}", response_model=Dict[str, Any])
async def get_file_trigger(trigger_id: str):
    """Get file trigger details by ID"""
    try:
        trigger = await file_watcher.get_file_trigger(trigger_id)
        if not trigger:
            raise HTTPException(status_code=404, detail="File trigger not found")
        return trigger
    except Exception as e:
        logger.error(f"Error getting file trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/file-triggers/{trigger_id}", response_model=Dict[str, str])
async def update_file_trigger(trigger_id: str, updates: FileTriggerUpdate):
    """Update a file trigger configuration"""
    try:
        # Filter out None values
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        success = await file_watcher.update_file_trigger(trigger_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="File trigger not found")
        
        return {"message": "File trigger updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating file trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/file-triggers/{trigger_id}", response_model=Dict[str, str])
async def delete_file_trigger(trigger_id: str):
    """Delete a file trigger"""
    try:
        success = await file_watcher.delete_file_trigger(trigger_id)
        if not success:
            raise HTTPException(status_code=404, detail="File trigger not found")
        
        return {"message": "File trigger deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting file trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/file-triggers/start-watching", response_model=Dict[str, str])
async def start_file_watching():
    """Start the file watcher service"""
    try:
        await file_watcher.start_watching()
        return {"message": "File watching started successfully"}
    except Exception as e:
        logger.error(f"Error starting file watcher: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/file-triggers/stop-watching", response_model=Dict[str, str])
async def stop_file_watching():
    """Stop the file watcher service"""
    try:
        await file_watcher.stop_watching()
        return {"message": "File watching stopped successfully"}
    except Exception as e:
        logger.error(f"Error stopping file watcher: {e}")
        raise HTTPException(status_code=500, detail=str(e))