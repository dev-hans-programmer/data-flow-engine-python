"""
Webhook handler service for real-time data ingestion
"""
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import Request
import logging
from ..utils.logger import get_logger
from ..database import get_db

logger = get_logger(__name__)

class WebhookHandler:
    """Handles incoming webhook data and triggers pipelines"""
    
    def __init__(self):
        self.webhook_configs = {}
        self.db = get_db()
    
    async def register_webhook(self, webhook_config: Dict[str, Any]) -> str:
        """Register a new webhook endpoint"""
        webhook_id = f"webhook_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Validate configuration
        required_fields = ['name', 'endpoint_path']
        for field in required_fields:
            if field not in webhook_config:
                raise ValueError(f"Missing required field: {field}")
        
        # Store webhook configuration
        self.webhook_configs[webhook_id] = {
            'id': webhook_id,
            'name': webhook_config['name'],
            'endpoint_path': webhook_config['endpoint_path'],
            'pipeline_id': webhook_config.get('pipeline_id'),
            'enabled': webhook_config.get('enabled', True),
            'secret_token': webhook_config.get('secret_token'),
            'data_mapping': webhook_config.get('data_mapping', {}),
            'created_at': datetime.utcnow(),
            'last_triggered': None,
            'trigger_count': 0
        }
        
        logger.info(f"Registered webhook: {webhook_id} at path {webhook_config['endpoint_path']}")
        return webhook_id
    
    async def process_webhook(self, endpoint_path: str, request: Request) -> Dict[str, Any]:
        """Process incoming webhook request"""
        # Find webhook config by endpoint path
        webhook_config = None
        for config in self.webhook_configs.values():
            if config['endpoint_path'] == endpoint_path and config['enabled']:
                webhook_config = config
                break
        
        if not webhook_config:
            logger.warning(f"No webhook found for path: {endpoint_path}")
            return {'status': 'error', 'message': 'Webhook not found'}
        
        try:
            # Validate secret token if configured
            if webhook_config.get('secret_token'):
                token_header = request.headers.get('X-Webhook-Token')
                if token_header != webhook_config['secret_token']:
                    logger.warning(f"Invalid token for webhook {webhook_config['id']}")
                    return {'status': 'error', 'message': 'Invalid token'}
            
            # Extract webhook data
            content_type = request.headers.get('content-type', '')
            if 'application/json' in content_type:
                webhook_data = await request.json()
            else:
                webhook_data = await request.body()
                webhook_data = webhook_data.decode('utf-8')
            
            # Apply data mapping if configured
            if webhook_config.get('data_mapping'):
                webhook_data = self._apply_data_mapping(webhook_data, webhook_config['data_mapping'])
            
            # Save webhook data and trigger pipeline
            result = await self._save_webhook_data_and_trigger(webhook_data, webhook_config, request)
            
            # Update webhook statistics
            webhook_config['last_triggered'] = datetime.utcnow()
            webhook_config['trigger_count'] += 1
            
            logger.info(f"Successfully processed webhook {webhook_config['id']}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing webhook {webhook_config['id']}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _apply_data_mapping(self, data: Any, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Apply data mapping transformations"""
        if not isinstance(data, dict):
            return data
        
        mapped_data = {}
        for target_field, source_path in mapping.items():
            # Simple dot notation support
            value = data
            for key in source_path.split('.'):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            mapped_data[target_field] = value
        
        return mapped_data
    
    async def _save_webhook_data_and_trigger(self, data: Any, webhook_config: Dict[str, Any], request: Request) -> Dict[str, Any]:
        """Save webhook data to file and trigger pipeline execution"""
        try:
            # Save data to file
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"webhook_data_{webhook_config['id']}_{timestamp}.json"
            filepath = f"uploads/{filename}"
            
            webhook_payload = {
                'data': data,
                'metadata': {
                    'webhook_id': webhook_config['id'],
                    'webhook_name': webhook_config['name'],
                    'timestamp': datetime.utcnow().isoformat(),
                    'source_ip': request.client.host if request.client else None,
                    'headers': dict(request.headers)
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(webhook_payload, f, indent=2, default=str)
            
            # Store file info
            await self.db.store_file_info({
                'name': filename,
                'path': filepath,
                'size': len(json.dumps(webhook_payload)),
                'format': 'json',
                'metadata': {
                    'source': 'webhook',
                    'webhook_id': webhook_config['id'],
                    'timestamp': datetime.utcnow().isoformat()
                }
            })
            
            # Trigger pipeline if configured
            if webhook_config.get('pipeline_id'):
                from ..pipeline_engine import PipelineEngine
                engine = PipelineEngine()
                pipeline = await self.db.get_pipeline(webhook_config['pipeline_id'])
                
                if pipeline:
                    execution = await engine.execute_pipeline(pipeline, {
                        'webhook_data_file': filepath,
                        'triggered_by': 'webhook',
                        'webhook_id': webhook_config['id']
                    })
                    logger.info(f"Triggered pipeline {webhook_config['pipeline_id']} from webhook")
                    
                    return {
                        'status': 'success',
                        'message': 'Webhook processed and pipeline triggered',
                        'execution_id': execution.id,
                        'file_saved': filepath
                    }
            
            return {
                'status': 'success',
                'message': 'Webhook processed successfully',
                'file_saved': filepath
            }
            
        except Exception as e:
            logger.error(f"Error saving webhook data and triggering pipeline: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all registered webhooks"""
        return list(self.webhook_configs.values())
    
    async def get_webhook(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """Get webhook configuration by ID"""
        return self.webhook_configs.get(webhook_id)
    
    async def update_webhook(self, webhook_id: str, updates: Dict[str, Any]) -> bool:
        """Update webhook configuration"""
        if webhook_id not in self.webhook_configs:
            return False
        
        webhook = self.webhook_configs[webhook_id]
        
        # Update allowed fields
        updatable_fields = ['name', 'endpoint_path', 'pipeline_id', 'enabled', 
                          'secret_token', 'data_mapping']
        
        for field in updatable_fields:
            if field in updates:
                webhook[field] = updates[field]
        
        logger.info(f"Updated webhook: {webhook_id}")
        return True
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook"""
        if webhook_id in self.webhook_configs:
            del self.webhook_configs[webhook_id]
            logger.info(f"Deleted webhook: {webhook_id}")
            return True
        return False

# Global webhook handler instance
webhook_handler = WebhookHandler()