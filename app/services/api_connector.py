"""
API connector service for external data ingestion
"""
import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from ..utils.logger import get_logger
from ..database import InMemoryDatabase

logger = get_logger(__name__)

class APIConnector:
    """Handles external API data ingestion"""
    
    def __init__(self):
        self.active_polls = {}
        self.db = get_db()
    
    async def create_api_source(self, source_config: Dict[str, Any]) -> str:
        """Create a new API data source"""
        source_id = f"api_source_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Validate configuration
        required_fields = ['name', 'url', 'method']
        for field in required_fields:
            if field not in source_config:
                raise ValueError(f"Missing required field: {field}")
        
        # Store source configuration
        self.active_polls[source_id] = {
            'id': source_id,
            'name': source_config['name'],
            'url': source_config['url'],
            'method': source_config.get('method', 'GET'),
            'headers': source_config.get('headers', {}),
            'params': source_config.get('params', {}),
            'poll_interval': source_config.get('poll_interval', 300),  # 5 minutes default
            'enabled': source_config.get('enabled', True),
            'last_poll': None,
            'created_at': datetime.utcnow(),
            'pipeline_id': source_config.get('pipeline_id'),
            'data_format': source_config.get('data_format', 'json'),
            'auth': source_config.get('auth', {})
        }
        
        logger.info(f"Created API source: {source_id}")
        return source_id
    
    async def fetch_api_data(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Fetch data from an API source"""
        if source_id not in self.active_polls:
            raise ValueError(f"API source not found: {source_id}")
        
        source = self.active_polls[source_id]
        
        try:
            async with aiohttp.ClientSession() as session:
                # Prepare request
                kwargs = {
                    'method': source['method'],
                    'url': source['url'],
                    'headers': source['headers'],
                    'params': source['params']
                }
                
                # Add authentication if provided
                if source['auth'].get('type') == 'bearer':
                    kwargs['headers']['Authorization'] = f"Bearer {source['auth']['token']}"
                elif source['auth'].get('type') == 'basic':
                    kwargs['auth'] = aiohttp.BasicAuth(
                        source['auth']['username'], 
                        source['auth']['password']
                    )
                
                async with session.request(**kwargs) as response:
                    if response.status == 200:
                        if source['data_format'] == 'json':
                            data = await response.json()
                        else:
                            data = await response.text()
                        
                        # Update last poll time
                        source['last_poll'] = datetime.utcnow()
                        
                        logger.info(f"Successfully fetched data from {source_id}")
                        return {
                            'source_id': source_id,
                            'data': data,
                            'timestamp': datetime.utcnow(),
                            'status': 'success'
                        }
                    else:
                        logger.error(f"API request failed with status {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching data from {source_id}: {e}")
            return None
    
    async def start_polling(self, source_id: str):
        """Start polling an API source"""
        if source_id not in self.active_polls:
            raise ValueError(f"API source not found: {source_id}")
        
        source = self.active_polls[source_id]
        
        async def poll_loop():
            while source['enabled']:
                try:
                    result = await self.fetch_api_data(source_id)
                    if result and source.get('pipeline_id'):
                        # Save data to file and trigger pipeline
                        await self._save_api_data_and_trigger(result, source)
                    
                    await asyncio.sleep(source['poll_interval'])
                    
                except Exception as e:
                    logger.error(f"Error in polling loop for {source_id}: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        # Start polling in background
        asyncio.create_task(poll_loop())
        logger.info(f"Started polling for API source: {source_id}")
    
    async def _save_api_data_and_trigger(self, result: Dict[str, Any], source: Dict[str, Any]):
        """Save API data to file and trigger pipeline execution"""
        try:
            # Save data to file
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"api_data_{source['id']}_{timestamp}.json"
            filepath = f"uploads/{filename}"
            
            with open(filepath, 'w') as f:
                json.dump(result['data'], f, indent=2, default=str)
            
            # Store file info
            await self.db.store_file_info({
                'name': filename,
                'path': filepath,
                'size': len(json.dumps(result['data'])),
                'format': 'json',
                'metadata': {
                    'source': 'api_ingestion',
                    'api_source_id': source['id'],
                    'timestamp': result['timestamp'].isoformat()
                }
            })
            
            # Trigger pipeline if configured
            if source.get('pipeline_id'):
                from ..pipeline_engine import PipelineEngine
                engine = PipelineEngine()
                pipeline = await self.db.get_pipeline(source['pipeline_id'])
                
                if pipeline:
                    await engine.execute_pipeline(pipeline, {
                        'api_data_file': filepath,
                        'triggered_by': 'api_polling'
                    })
                    logger.info(f"Triggered pipeline {source['pipeline_id']} with API data")
            
        except Exception as e:
            logger.error(f"Error saving API data and triggering pipeline: {e}")
    
    async def list_api_sources(self) -> List[Dict[str, Any]]:
        """List all API sources"""
        return list(self.active_polls.values())
    
    async def update_api_source(self, source_id: str, updates: Dict[str, Any]) -> bool:
        """Update an API source configuration"""
        if source_id not in self.active_polls:
            return False
        
        source = self.active_polls[source_id]
        
        # Update allowed fields
        updatable_fields = ['name', 'url', 'method', 'headers', 'params', 
                          'poll_interval', 'enabled', 'pipeline_id', 'auth']
        
        for field in updatable_fields:
            if field in updates:
                source[field] = updates[field]
        
        logger.info(f"Updated API source: {source_id}")
        return True
    
    async def delete_api_source(self, source_id: str) -> bool:
        """Delete an API source"""
        if source_id in self.active_polls:
            # Disable polling first
            self.active_polls[source_id]['enabled'] = False
            del self.active_polls[source_id]
            logger.info(f"Deleted API source: {source_id}")
            return True
        return False

# Global API connector instance
api_connector = APIConnector()