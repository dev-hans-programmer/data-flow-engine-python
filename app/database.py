"""
In-memory database implementation for pipeline management
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
from app.models import Pipeline, Execution, FileInfo, PipelineStatus, ExecutionStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InMemoryDatabase:
    """In-memory database for storing pipeline data"""
    
    def __init__(self):
        self.pipelines: Dict[str, Pipeline] = {}
        self.executions: Dict[str, Execution] = {}
        self.files: Dict[str, FileInfo] = {}
        self._lock = asyncio.Lock()
        self._data_file = "data/database.json"
        self._load_data()
    
    def _load_data(self):
        """Load data from file if exists"""
        try:
            if os.path.exists(self._data_file):
                with open(self._data_file, 'r') as f:
                    data = json.load(f)
                
                # Load pipelines
                for pipeline_data in data.get('pipelines', []):
                    pipeline = Pipeline(**pipeline_data)
                    self.pipelines[pipeline.id] = pipeline
                
                # Load executions
                for execution_data in data.get('executions', []):
                    execution = Execution(**execution_data)
                    self.executions[execution.id] = execution
                
                # Load files
                for file_data in data.get('files', []):
                    file_info = FileInfo(**file_data)
                    self.files[file_info.path] = file_info
                
                logger.info(f"Loaded data: {len(self.pipelines)} pipelines, {len(self.executions)} executions, {len(self.files)} files")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def _save_data(self):
        """Save data to file"""
        try:
            os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
            
            data = {
                'pipelines': [pipeline.dict() for pipeline in self.pipelines.values()],
                'executions': [execution.dict() for execution in self.executions.values()],
                'files': [file_info.dict() for file_info in self.files.values()]
            }
            
            with open(self._data_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    # Pipeline operations
    async def create_pipeline(self, pipeline: Pipeline) -> Pipeline:
        """Create a new pipeline"""
        async with self._lock:
            self.pipelines[pipeline.id] = pipeline
            self._save_data()
            logger.info(f"Created pipeline: {pipeline.id}")
            return pipeline
    
    async def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get pipeline by ID"""
        return self.pipelines.get(pipeline_id)
    
    async def list_pipelines(self, 
                           skip: int = 0, 
                           limit: int = 100,
                           status: Optional[PipelineStatus] = None) -> List[Pipeline]:
        """List pipelines with pagination and filtering"""
        pipelines = list(self.pipelines.values())
        
        if status:
            pipelines = [p for p in pipelines if p.status == status]
        
        # Sort by created_at descending
        pipelines.sort(key=lambda x: x.created_at, reverse=True)
        
        return pipelines[skip:skip + limit]
    
    async def update_pipeline(self, pipeline_id: str, pipeline: Pipeline) -> Optional[Pipeline]:
        """Update an existing pipeline"""
        async with self._lock:
            if pipeline_id in self.pipelines:
                pipeline.updated_at = datetime.utcnow()
                self.pipelines[pipeline_id] = pipeline
                self._save_data()
                logger.info(f"Updated pipeline: {pipeline_id}")
                return pipeline
            return None
    
    async def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete a pipeline"""
        async with self._lock:
            if pipeline_id in self.pipelines:
                self.pipelines[pipeline_id].status = PipelineStatus.DELETED
                self._save_data()
                logger.info(f"Deleted pipeline: {pipeline_id}")
                return True
            return False
    
    # Execution operations
    async def create_execution(self, execution: Execution) -> Execution:
        """Create a new execution"""
        async with self._lock:
            self.executions[execution.id] = execution
            self._save_data()
            logger.info(f"Created execution: {execution.id}")
            return execution
    
    async def get_execution(self, execution_id: str) -> Optional[Execution]:
        """Get execution by ID"""
        return self.executions.get(execution_id)
    
    async def list_executions(self, 
                            skip: int = 0, 
                            limit: int = 100,
                            pipeline_id: Optional[str] = None,
                            status: Optional[ExecutionStatus] = None) -> List[Execution]:
        """List executions with pagination and filtering"""
        executions = list(self.executions.values())
        
        if pipeline_id:
            executions = [e for e in executions if e.pipeline_id == pipeline_id]
        
        if status:
            executions = [e for e in executions if e.status == status]
        
        # Sort by created_at descending
        executions.sort(key=lambda x: x.created_at, reverse=True)
        
        return executions[skip:skip + limit]
    
    async def update_execution(self, execution_id: str, execution: Execution) -> Optional[Execution]:
        """Update an existing execution"""
        async with self._lock:
            if execution_id in self.executions:
                self.executions[execution_id] = execution
                self._save_data()
                return execution
            return None
    
    # File operations
    async def store_file_info(self, file_info: FileInfo) -> FileInfo:
        """Store file information"""
        async with self._lock:
            self.files[file_info.path] = file_info
            self._save_data()
            logger.info(f"Stored file info: {file_info.path}")
            return file_info
    
    async def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """Get file information"""
        return self.files.get(file_path)
    
    async def list_files(self) -> List[FileInfo]:
        """List all files"""
        return list(self.files.values())
    
    async def delete_file_info(self, file_path: str) -> bool:
        """Delete file information"""
        async with self._lock:
            if file_path in self.files:
                del self.files[file_path]
                self._save_data()
                logger.info(f"Deleted file info: {file_path}")
                return True
            return False
    
    # Statistics
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            "pipelines": {
                "total": len(self.pipelines),
                "active": len([p for p in self.pipelines.values() if p.status == PipelineStatus.ACTIVE]),
                "draft": len([p for p in self.pipelines.values() if p.status == PipelineStatus.DRAFT]),
                "inactive": len([p for p in self.pipelines.values() if p.status == PipelineStatus.INACTIVE])
            },
            "executions": {
                "total": len(self.executions),
                "running": len([e for e in self.executions.values() if e.status == ExecutionStatus.RUNNING]),
                "completed": len([e for e in self.executions.values() if e.status == ExecutionStatus.COMPLETED]),
                "failed": len([e for e in self.executions.values() if e.status == ExecutionStatus.FAILED])
            },
            "files": {
                "total": len(self.files),
                "total_size": sum(f.size for f in self.files.values())
            }
        }


# Global database instance
db = InMemoryDatabase()
