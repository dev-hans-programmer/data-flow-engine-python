"""
File watcher service for event-driven pipeline triggers
"""
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List, Callable
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from ..utils.logger import get_logger
from ..database import InMemoryDatabase

logger = get_logger(__name__)

class FileUploadHandler(FileSystemEventHandler):
    """Handles file system events for uploaded files"""
    
    def __init__(self, file_watcher):
        self.file_watcher = file_watcher
        
    def on_created(self, event):
        """Called when a file is created"""
        if not event.is_directory:
            asyncio.create_task(self.file_watcher.handle_file_upload(event.src_path))
    
    def on_modified(self, event):
        """Called when a file is modified"""
        if not event.is_directory:
            asyncio.create_task(self.file_watcher.handle_file_upload(event.src_path))

class FileWatcher:
    """Watches for file uploads and triggers pipelines"""
    
    def __init__(self):
        self.triggers = {}
        self.observer = Observer()
        self.db = InMemoryDatabase()
        self.is_watching = False
        
    async def register_file_trigger(self, trigger_config: Dict[str, Any]) -> str:
        """Register a file upload trigger"""
        trigger_id = f"file_trigger_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Validate configuration
        required_fields = ['name', 'watch_path', 'pipeline_id']
        for field in required_fields:
            if field not in trigger_config:
                raise ValueError(f"Missing required field: {field}")
        
        self.triggers[trigger_id] = {
            'id': trigger_id,
            'name': trigger_config['name'],
            'watch_path': trigger_config['watch_path'],
            'pipeline_id': trigger_config['pipeline_id'],
            'file_patterns': trigger_config.get('file_patterns', ['*']),
            'enabled': trigger_config.get('enabled', True),
            'created_at': datetime.utcnow(),
            'trigger_count': 0,
            'last_triggered': None
        }
        
        logger.info(f"Registered file trigger: {trigger_id}")
        return trigger_id
    
    async def start_watching(self):
        """Start watching for file changes"""
        if self.is_watching:
            return
            
        # Set up file system observer
        handler = FileUploadHandler(self)
        
        # Watch the uploads directory
        upload_path = "uploads"
        os.makedirs(upload_path, exist_ok=True)
        
        self.observer.schedule(handler, upload_path, recursive=True)
        self.observer.start()
        self.is_watching = True
        
        logger.info("File watcher started")
    
    async def stop_watching(self):
        """Stop watching for file changes"""
        if self.is_watching:
            self.observer.stop()
            self.observer.join()
            self.is_watching = False
            logger.info("File watcher stopped")
    
    async def handle_file_upload(self, file_path: str):
        """Handle a file upload event"""
        try:
            # Check if file exists and is complete
            if not os.path.exists(file_path):
                return
                
            # Get file info
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            
            # Wait a moment to ensure file is completely written
            await asyncio.sleep(1)
            
            # Check if file size changed (still being written)
            if os.path.exists(file_path):
                new_stat = os.stat(file_path)
                if new_stat.st_size != file_size:
                    return  # File still being written
            
            # Find matching triggers
            matching_triggers = await self._find_matching_triggers(file_path)
            
            for trigger in matching_triggers:
                if trigger['enabled']:
                    await self._execute_trigger(trigger, file_path)
                    
        except Exception as e:
            logger.error(f"Error handling file upload {file_path}: {e}")
    
    async def _find_matching_triggers(self, file_path: str) -> List[Dict[str, Any]]:
        """Find triggers that match the uploaded file"""
        matching = []
        
        for trigger in self.triggers.values():
            # Check if file path matches watch path
            if trigger['watch_path'] in file_path or trigger['watch_path'] == '*':
                # Check file patterns
                file_name = os.path.basename(file_path)
                patterns = trigger['file_patterns']
                
                if '*' in patterns:
                    matching.append(trigger)
                else:
                    for pattern in patterns:
                        if pattern in file_name or file_name.endswith(pattern):
                            matching.append(trigger)
                            break
        
        return matching
    
    async def _execute_trigger(self, trigger: Dict[str, Any], file_path: str):
        """Execute a pipeline trigger"""
        try:
            from ..pipeline_engine import PipelineEngine
            
            engine = PipelineEngine()
            pipeline = await self.db.get_pipeline(trigger['pipeline_id'])
            
            if not pipeline:
                logger.error(f"Pipeline {trigger['pipeline_id']} not found for trigger {trigger['id']}")
                return
            
            # Execute pipeline with file information
            execution = await engine.execute_pipeline(pipeline, {
                'triggered_file': file_path,
                'triggered_by': 'file_upload',
                'trigger_id': trigger['id'],
                'trigger_name': trigger['name']
            })
            
            # Update trigger statistics
            trigger['trigger_count'] += 1
            trigger['last_triggered'] = datetime.utcnow()
            
            logger.info(f"Triggered pipeline {pipeline.id} from file upload: {file_path}")
            
        except Exception as e:
            logger.error(f"Error executing trigger {trigger['id']}: {e}")
    
    async def list_file_triggers(self) -> List[Dict[str, Any]]:
        """List all file triggers"""
        return list(self.triggers.values())
    
    async def get_file_trigger(self, trigger_id: str) -> Dict[str, Any]:
        """Get file trigger by ID"""
        return self.triggers.get(trigger_id)
    
    async def update_file_trigger(self, trigger_id: str, updates: Dict[str, Any]) -> bool:
        """Update a file trigger"""
        if trigger_id not in self.triggers:
            return False
        
        trigger = self.triggers[trigger_id]
        
        # Update allowed fields
        updatable_fields = ['name', 'watch_path', 'pipeline_id', 'file_patterns', 'enabled']
        
        for field in updatable_fields:
            if field in updates:
                trigger[field] = updates[field]
        
        logger.info(f"Updated file trigger: {trigger_id}")
        return True
    
    async def delete_file_trigger(self, trigger_id: str) -> bool:
        """Delete a file trigger"""
        if trigger_id in self.triggers:
            del self.triggers[trigger_id]
            logger.info(f"Deleted file trigger: {trigger_id}")
            return True
        return False

# Global file watcher instance
file_watcher = FileWatcher()