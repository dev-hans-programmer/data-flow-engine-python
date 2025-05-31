"""
PostgreSQL database service for pipeline management
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_, or_
from datetime import datetime
import uuid

from app.db_models import Pipeline as DBPipeline, Execution as DBExecution, FileInfo as DBFileInfo
from app.db_models import ApiSource as DBApiSource, WebhookConfig as DBWebhookConfig, TriggerConfig as DBTriggerConfig
from app.models import Pipeline, Execution, FileInfo, PipelineStatus, ExecutionStatus
from app.db_connection import AsyncSessionLocal
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseService:
    """PostgreSQL database service for storing pipeline data"""
    
    def __init__(self):
        pass
    
    async def get_session(self) -> AsyncSession:
        """Get database session"""
        return AsyncSessionLocal()
    
    # Pipeline operations
    async def create_pipeline(self, pipeline: Pipeline) -> Pipeline:
        """Create a new pipeline"""
        async with self.get_session() as session:
            try:
                db_pipeline = DBPipeline(
                    id=pipeline.id,
                    name=pipeline.name,
                    description=pipeline.description,
                    status=pipeline.status,
                    steps=[step.dict() for step in pipeline.steps],
                    schedule=pipeline.schedule.dict() if pipeline.schedule else None,
                    metadata=pipeline.metadata,
                    created_at=pipeline.created_at,
                    updated_at=pipeline.updated_at,
                    created_by=pipeline.created_by
                )
                session.add(db_pipeline)
                await session.commit()
                await session.refresh(db_pipeline)
                
                logger.info(f"Created pipeline: {pipeline.id}")
                return pipeline
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error creating pipeline: {e}")
                raise
    
    async def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get pipeline by ID"""
        async with self.get_session() as session:
            try:
                result = await session.execute(
                    select(DBPipeline).where(DBPipeline.id == pipeline_id)
                )
                db_pipeline = result.scalar_one_or_none()
                
                if not db_pipeline:
                    return None
                
                return self._convert_db_pipeline_to_model(db_pipeline)
                
            except Exception as e:
                logger.error(f"Error getting pipeline {pipeline_id}: {e}")
                raise
    
    async def list_pipelines(self, 
                           skip: int = 0, 
                           limit: int = 100,
                           status: Optional[PipelineStatus] = None) -> List[Pipeline]:
        """List pipelines with pagination and filtering"""
        async with self.get_session() as session:
            try:
                query = select(DBPipeline)
                
                if status:
                    query = query.where(DBPipeline.status == status)
                
                query = query.offset(skip).limit(limit).order_by(DBPipeline.created_at.desc())
                
                result = await session.execute(query)
                db_pipelines = result.scalars().all()
                
                return [self._convert_db_pipeline_to_model(db_pipeline) for db_pipeline in db_pipelines]
                
            except Exception as e:
                logger.error(f"Error listing pipelines: {e}")
                raise
    
    async def update_pipeline(self, pipeline_id: str, pipeline: Pipeline) -> Optional[Pipeline]:
        """Update an existing pipeline"""
        async with self.get_session() as session:
            try:
                result = await session.execute(
                    select(DBPipeline).where(DBPipeline.id == pipeline_id)
                )
                db_pipeline = result.scalar_one_or_none()
                
                if not db_pipeline:
                    return None
                
                # Update fields
                db_pipeline.name = pipeline.name
                db_pipeline.description = pipeline.description
                db_pipeline.status = pipeline.status
                db_pipeline.steps = [step.dict() for step in pipeline.steps]
                db_pipeline.schedule = pipeline.schedule.dict() if pipeline.schedule else None
                db_pipeline.metadata = pipeline.metadata
                db_pipeline.updated_at = datetime.utcnow()
                
                await session.commit()
                
                logger.info(f"Updated pipeline: {pipeline_id}")
                return self._convert_db_pipeline_to_model(db_pipeline)
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating pipeline {pipeline_id}: {e}")
                raise
    
    async def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete a pipeline"""
        async with self.get_session() as session:
            try:
                result = await session.execute(
                    select(DBPipeline).where(DBPipeline.id == pipeline_id)
                )
                db_pipeline = result.scalar_one_or_none()
                
                if not db_pipeline:
                    return False
                
                await session.delete(db_pipeline)
                await session.commit()
                
                logger.info(f"Deleted pipeline: {pipeline_id}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error deleting pipeline {pipeline_id}: {e}")
                raise
    
    # Execution operations
    async def create_execution(self, execution: Execution) -> Execution:
        """Create a new execution"""
        async with self.get_session() as session:
            try:
                db_execution = DBExecution(
                    id=execution.id,
                    pipeline_id=execution.pipeline_id,
                    pipeline_name=execution.pipeline_name,
                    status=execution.status,
                    start_time=execution.start_time,
                    end_time=execution.end_time,
                    duration=execution.duration,
                    parameters=execution.parameters,
                    triggered_by=execution.triggered_by,
                    steps=[step.dict() for step in execution.steps],
                    error_message=execution.error_message,
                    output_files=execution.output_files,
                    logs=execution.logs,
                    created_at=execution.created_at
                )
                session.add(db_execution)
                await session.commit()
                await session.refresh(db_execution)
                
                logger.info(f"Created execution: {execution.id}")
                return execution
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error creating execution: {e}")
                raise
    
    async def get_execution(self, execution_id: str) -> Optional[Execution]:
        """Get execution by ID"""
        async with self.get_session() as session:
            try:
                result = await session.execute(
                    select(DBExecution).where(DBExecution.id == execution_id)
                )
                db_execution = result.scalar_one_or_none()
                
                if not db_execution:
                    return None
                
                return self._convert_db_execution_to_model(db_execution)
                
            except Exception as e:
                logger.error(f"Error getting execution {execution_id}: {e}")
                raise
    
    async def list_executions(self, 
                            skip: int = 0, 
                            limit: int = 100,
                            pipeline_id: Optional[str] = None,
                            status: Optional[ExecutionStatus] = None) -> List[Execution]:
        """List executions with pagination and filtering"""
        async with self.get_session() as session:
            try:
                query = select(DBExecution)
                
                conditions = []
                if pipeline_id:
                    conditions.append(DBExecution.pipeline_id == pipeline_id)
                if status:
                    conditions.append(DBExecution.status == status)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.offset(skip).limit(limit).order_by(DBExecution.created_at.desc())
                
                result = await session.execute(query)
                db_executions = result.scalars().all()
                
                return [self._convert_db_execution_to_model(db_execution) for db_execution in db_executions]
                
            except Exception as e:
                logger.error(f"Error listing executions: {e}")
                raise
    
    async def update_execution(self, execution_id: str, execution: Execution) -> Optional[Execution]:
        """Update an existing execution"""
        async with self.get_session() as session:
            try:
                result = await session.execute(
                    select(DBExecution).where(DBExecution.id == execution_id)
                )
                db_execution = result.scalar_one_or_none()
                
                if not db_execution:
                    return None
                
                # Update fields
                db_execution.status = execution.status
                db_execution.start_time = execution.start_time
                db_execution.end_time = execution.end_time
                db_execution.duration = execution.duration
                db_execution.steps = [step.dict() for step in execution.steps]
                db_execution.error_message = execution.error_message
                db_execution.output_files = execution.output_files
                db_execution.logs = execution.logs
                
                await session.commit()
                
                logger.info(f"Updated execution: {execution_id}")
                return self._convert_db_execution_to_model(db_execution)
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating execution {execution_id}: {e}")
                raise
    
    # File operations
    async def store_file_info(self, file_info: FileInfo) -> FileInfo:
        """Store file information"""
        async with self.get_session() as session:
            try:
                db_file_info = DBFileInfo(
                    name=file_info.name,
                    path=file_info.path,
                    size=file_info.size,
                    format=file_info.format,
                    uploaded_at=file_info.uploaded_at,
                    metadata=file_info.metadata
                )
                session.add(db_file_info)
                await session.commit()
                await session.refresh(db_file_info)
                
                logger.info(f"Stored file info: {file_info.path}")
                return file_info
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error storing file info: {e}")
                raise
    
    async def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """Get file information"""
        async with self.get_session() as session:
            try:
                result = await session.execute(
                    select(DBFileInfo).where(DBFileInfo.path == file_path)
                )
                db_file_info = result.scalar_one_or_none()
                
                if not db_file_info:
                    return None
                
                return FileInfo(
                    name=db_file_info.name,
                    path=db_file_info.path,
                    size=db_file_info.size,
                    format=db_file_info.format,
                    uploaded_at=db_file_info.uploaded_at,
                    metadata=db_file_info.metadata
                )
                
            except Exception as e:
                logger.error(f"Error getting file info {file_path}: {e}")
                raise
    
    async def list_files(self) -> List[FileInfo]:
        """List all files"""
        async with self.get_session() as session:
            try:
                result = await session.execute(
                    select(DBFileInfo).order_by(DBFileInfo.uploaded_at.desc())
                )
                db_files = result.scalars().all()
                
                return [
                    FileInfo(
                        name=db_file.name,
                        path=db_file.path,
                        size=db_file.size,
                        format=db_file.format,
                        uploaded_at=db_file.uploaded_at,
                        metadata=db_file.metadata
                    )
                    for db_file in db_files
                ]
                
            except Exception as e:
                logger.error(f"Error listing files: {e}")
                raise
    
    async def delete_file_info(self, file_path: str) -> bool:
        """Delete file information"""
        async with self.get_session() as session:
            try:
                result = await session.execute(
                    select(DBFileInfo).where(DBFileInfo.path == file_path)
                )
                db_file_info = result.scalar_one_or_none()
                
                if not db_file_info:
                    return False
                
                await session.delete(db_file_info)
                await session.commit()
                
                logger.info(f"Deleted file info: {file_path}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error deleting file info {file_path}: {e}")
                raise
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        async with self.get_session() as session:
            try:
                # Count pipelines by status
                pipeline_stats = await session.execute(
                    select(DBPipeline.status, func.count(DBPipeline.id))
                    .group_by(DBPipeline.status)
                )
                
                # Count executions by status
                execution_stats = await session.execute(
                    select(DBExecution.status, func.count(DBExecution.id))
                    .group_by(DBExecution.status)
                )
                
                # Count total files
                file_count = await session.execute(
                    select(func.count(DBFileInfo.id))
                )
                
                return {
                    "pipelines": dict(pipeline_stats.all()),
                    "executions": dict(execution_stats.all()),
                    "files": file_count.scalar()
                }
                
            except Exception as e:
                logger.error(f"Error getting statistics: {e}")
                raise
    
    def _convert_db_pipeline_to_model(self, db_pipeline: DBPipeline) -> Pipeline:
        """Convert database pipeline to Pydantic model"""
        from app.models import LoadStep, TransformStep, FilterStep, AggregateStep, JoinStep, SaveStep, ScheduleConfig
        
        # Convert steps from JSON to step objects
        steps = []
        for step_data in db_pipeline.steps:
            step_type = step_data.get('type')
            if step_type == 'load':
                steps.append(LoadStep(**step_data))
            elif step_type == 'transform':
                steps.append(TransformStep(**step_data))
            elif step_type == 'filter':
                steps.append(FilterStep(**step_data))
            elif step_type == 'aggregate':
                steps.append(AggregateStep(**step_data))
            elif step_type == 'join':
                steps.append(JoinStep(**step_data))
            elif step_type == 'save':
                steps.append(SaveStep(**step_data))
        
        # Convert schedule from JSON
        schedule = None
        if db_pipeline.schedule:
            schedule = ScheduleConfig(**db_pipeline.schedule)
        
        return Pipeline(
            id=db_pipeline.id,
            name=db_pipeline.name,
            description=db_pipeline.description,
            status=db_pipeline.status,
            steps=steps,
            schedule=schedule,
            metadata=db_pipeline.metadata,
            created_at=db_pipeline.created_at,
            updated_at=db_pipeline.updated_at,
            created_by=db_pipeline.created_by
        )
    
    def _convert_db_execution_to_model(self, db_execution: DBExecution) -> Execution:
        """Convert database execution to Pydantic model"""
        from app.models import StepExecution
        
        # Convert steps from JSON to step execution objects
        steps = []
        for step_data in db_execution.steps:
            steps.append(StepExecution(**step_data))
        
        return Execution(
            id=db_execution.id,
            pipeline_id=db_execution.pipeline_id,
            pipeline_name=db_execution.pipeline_name,
            status=db_execution.status,
            start_time=db_execution.start_time,
            end_time=db_execution.end_time,
            duration=db_execution.duration,
            parameters=db_execution.parameters,
            triggered_by=db_execution.triggered_by,
            steps=steps,
            error_message=db_execution.error_message,
            output_files=db_execution.output_files,
            logs=db_execution.logs,
            created_at=db_execution.created_at
        )


# Global database service instance
db_service = DatabaseService()