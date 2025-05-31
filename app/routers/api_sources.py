"""
API routes for external data source management
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from ..services.api_connector import api_connector
from ..services.webhook_handler import webhook_handler
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

class APISourceCreate(BaseModel):
    name: str
    url: str
    method: str = "GET"
    headers: Dict[str, str] = {}
    params: Dict[str, str] = {}
    poll_interval: int = 300
    enabled: bool = True
    pipeline_id: Optional[str] = None
    data_format: str = "json"
    auth: Dict[str, Any] = {}

class APISourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, str]] = None
    poll_interval: Optional[int] = None
    enabled: Optional[bool] = None
    pipeline_id: Optional[str] = None
    auth: Optional[Dict[str, Any]] = None

class WebhookCreate(BaseModel):
    name: str
    endpoint_path: str
    pipeline_id: Optional[str] = None
    enabled: bool = True
    secret_token: Optional[str] = None
    data_mapping: Dict[str, str] = {}

class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    endpoint_path: Optional[str] = None
    pipeline_id: Optional[str] = None
    enabled: Optional[bool] = None
    secret_token: Optional[str] = None
    data_mapping: Optional[Dict[str, str]] = None

# API Source endpoints
@router.post("/api-sources", response_model=Dict[str, str])
async def create_api_source(source: APISourceCreate):
    """Create a new API data source"""
    try:
        source_id = await api_connector.create_api_source(source.dict())
        
        # Start polling if enabled
        if source.enabled:
            await api_connector.start_polling(source_id)
        
        return {"source_id": source_id, "message": "API source created successfully"}
        
    except Exception as e:
        logger.error(f"Error creating API source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api-sources", response_model=List[Dict[str, Any]])
async def list_api_sources():
    """List all API data sources"""
    try:
        sources = await api_connector.list_api_sources()
        return sources
    except Exception as e:
        logger.error(f"Error listing API sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api-sources/{source_id}", response_model=Dict[str, str])
async def update_api_source(source_id: str, updates: APISourceUpdate):
    """Update an API data source"""
    try:
        # Filter out None values
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        success = await api_connector.update_api_source(source_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="API source not found")
        
        return {"message": "API source updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating API source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api-sources/{source_id}", response_model=Dict[str, str])
async def delete_api_source(source_id: str):
    """Delete an API data source"""
    try:
        success = await api_connector.delete_api_source(source_id)
        if not success:
            raise HTTPException(status_code=404, detail="API source not found")
        
        return {"message": "API source deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting API source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api-sources/{source_id}/test", response_model=Dict[str, Any])
async def test_api_source(source_id: str):
    """Test an API data source connection"""
    try:
        result = await api_connector.fetch_api_data(source_id)
        if result:
            return {"status": "success", "message": "API connection successful", "data_preview": str(result)[:500]}
        else:
            return {"status": "error", "message": "Failed to fetch data from API"}
            
    except Exception as e:
        logger.error(f"Error testing API source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Webhook endpoints
@router.post("/webhooks", response_model=Dict[str, str])
async def create_webhook(webhook: WebhookCreate):
    """Create a new webhook endpoint"""
    try:
        webhook_id = await webhook_handler.register_webhook(webhook.dict())
        return {"webhook_id": webhook_id, "message": "Webhook created successfully"}
        
    except Exception as e:
        logger.error(f"Error creating webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/webhooks", response_model=List[Dict[str, Any]])
async def list_webhooks():
    """List all registered webhooks"""
    try:
        webhooks = await webhook_handler.list_webhooks()
        return webhooks
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/webhooks/{webhook_id}", response_model=Dict[str, Any])
async def get_webhook(webhook_id: str):
    """Get webhook details by ID"""
    try:
        webhook = await webhook_handler.get_webhook(webhook_id)
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        return webhook
    except Exception as e:
        logger.error(f"Error getting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/webhooks/{webhook_id}", response_model=Dict[str, str])
async def update_webhook(webhook_id: str, updates: WebhookUpdate):
    """Update a webhook configuration"""
    try:
        # Filter out None values
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        success = await webhook_handler.update_webhook(webhook_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        return {"message": "Webhook updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/webhooks/{webhook_id}", response_model=Dict[str, str])
async def delete_webhook(webhook_id: str):
    """Delete a webhook"""
    try:
        success = await webhook_handler.delete_webhook(webhook_id)
        if not success:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        return {"message": "Webhook deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dynamic webhook receiver endpoint
@router.post("/webhook/{endpoint_path:path}", response_model=Dict[str, Any])
async def receive_webhook(endpoint_path: str, request: Request):
    """Receive incoming webhook data"""
    try:
        result = await webhook_handler.process_webhook(endpoint_path, request)
        return result
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))