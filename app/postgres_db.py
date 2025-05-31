"""
Simple PostgreSQL database implementation using asyncpg directly
"""

import asyncpg
import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models import Pipeline, Execution, FileInfo, PipelineStatus, ExecutionStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PostgreSQLDatabase:
    """PostgreSQL database for storing pipeline data"""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        self.connection_pool = None
    
    async def init_database(self):
        """Initialize database connection pool and create tables"""
        try:
            self.connection_pool = await asyncpg.create_pool(self.database_url)
            await self._create_tables()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    async def close_database(self):
        """Close database connection pool"""
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("Database connections closed")
    
    async def _create_tables(self):
        """Create database tables if they don't exist"""
        async with self.connection_pool.acquire() as conn:
            # Create pipelines table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pipelines (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    description TEXT,
                    status VARCHAR DEFAULT 'draft',
                    steps JSONB NOT NULL,
                    schedule JSONB,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    created_by VARCHAR
                )
            """)
            
            # Create executions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id VARCHAR PRIMARY KEY,
                    pipeline_id VARCHAR NOT NULL,
                    pipeline_name VARCHAR NOT NULL,
                    status VARCHAR DEFAULT 'pending',
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration FLOAT,
                    parameters JSONB DEFAULT '{}',
                    triggered_by VARCHAR,
                    steps JSONB DEFAULT '[]',
                    error_message TEXT,
                    output_files JSONB DEFAULT '[]',
                    logs JSONB DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create file_info table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS file_info (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    path VARCHAR NOT NULL UNIQUE,
                    size BIGINT NOT NULL,
                    format VARCHAR,
                    uploaded_at TIMESTAMP DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            """)
            
            logger.info("Database tables created successfully")
    
    # Pipeline operations
    async def create_pipeline(self, pipeline: Pipeline) -> Pipeline:
        """Create a new pipeline"""
        async with self.connection_pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO pipelines (id, name, description, status, steps, schedule, metadata, created_at, updated_at, created_by)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, 
                    pipeline.id,
                    pipeline.name,
                    pipeline.description,
                    pipeline.status.value,
                    json.dumps([step.dict() for step in pipeline.steps]),
                    json.dumps(pipeline.schedule.dict()) if pipeline.schedule else None,
                    json.dumps(pipeline.metadata),
                    pipeline.created_at,
                    pipeline.updated_at,
                    pipeline.created_by
                )
                
                logger.info(f"Created pipeline: {pipeline.id}")
                return pipeline
                
            except Exception as e:
                logger.error(f"Error creating pipeline: {e}")
                raise
    
    async def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get pipeline by ID"""
        async with self.connection_pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    "SELECT * FROM pipelines WHERE id = $1", pipeline_id
                )
                
                if not row:
                    return None
                
                return self._row_to_pipeline(row)
                
            except Exception as e:
                logger.error(f"Error getting pipeline {pipeline_id}: {e}")
                raise
    
    async def list_pipelines(self, skip: int = 0, limit: int = 100, status: Optional[PipelineStatus] = None) -> List[Pipeline]:
        """List pipelines with pagination and filtering"""
        async with self.connection_pool.acquire() as conn:
            try:
                query = "SELECT * FROM pipelines"
                params = []
                
                if status:
                    query += " WHERE status = $1"
                    params.append(status.value)
                
                query += " ORDER BY created_at DESC OFFSET $" + str(len(params) + 1) + " LIMIT $" + str(len(params) + 2)
                params.extend([skip, limit])
                
                rows = await conn.fetch(query, *params)
                return [self._row_to_pipeline(row) for row in rows]
                
            except Exception as e:
                logger.error(f"Error listing pipelines: {e}")
                raise
    
    async def update_pipeline(self, pipeline_id: str, pipeline: Pipeline) -> Optional[Pipeline]:
        """Update an existing pipeline"""
        async with self.connection_pool.acquire() as conn:
            try:
                result = await conn.execute("""
                    UPDATE pipelines 
                    SET name = $2, description = $3, status = $4, steps = $5, 
                        schedule = $6, metadata = $7, updated_at = $8
                    WHERE id = $1
                """,
                    pipeline_id,
                    pipeline.name,
                    pipeline.description,
                    pipeline.status.value,
                    json.dumps([step.dict() for step in pipeline.steps]),
                    json.dumps(pipeline.schedule.dict()) if pipeline.schedule else None,
                    json.dumps(pipeline.metadata),
                    datetime.utcnow()
                )
                
                if result == "UPDATE 0":
                    return None
                
                logger.info(f"Updated pipeline: {pipeline_id}")
                return pipeline
                
            except Exception as e:
                logger.error(f"Error updating pipeline {pipeline_id}: {e}")
                raise
    
    async def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete a pipeline"""
        async with self.connection_pool.acquire() as conn:
            try:
                result = await conn.execute(
                    "DELETE FROM pipelines WHERE id = $1", pipeline_id
                )
                
                success = result != "DELETE 0"
                if success:
                    logger.info(f"Deleted pipeline: {pipeline_id}")
                
                return success
                
            except Exception as e:
                logger.error(f"Error deleting pipeline {pipeline_id}: {e}")
                raise
    
    # Execution operations
    async def create_execution(self, execution: Execution) -> Execution:
        """Create a new execution"""
        async with self.connection_pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO executions (id, pipeline_id, pipeline_name, status, start_time, end_time, 
                                          duration, parameters, triggered_by, steps, error_message, 
                                          output_files, logs, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """,
                    execution.id,
                    execution.pipeline_id,
                    execution.pipeline_name,
                    execution.status.value,
                    execution.start_time,
                    execution.end_time,
                    execution.duration,
                    json.dumps(execution.parameters),
                    execution.triggered_by,
                    json.dumps([step.dict() for step in execution.steps]),
                    execution.error_message,
                    json.dumps(execution.output_files),
                    json.dumps(execution.logs),
                    execution.created_at
                )
                
                logger.info(f"Created execution: {execution.id}")
                return execution
                
            except Exception as e:
                logger.error(f"Error creating execution: {e}")
                raise
    
    async def get_execution(self, execution_id: str) -> Optional[Execution]:
        """Get execution by ID"""
        async with self.connection_pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    "SELECT * FROM executions WHERE id = $1", execution_id
                )
                
                if not row:
                    return None
                
                return self._row_to_execution(row)
                
            except Exception as e:
                logger.error(f"Error getting execution {execution_id}: {e}")
                raise
    
    async def list_executions(self, skip: int = 0, limit: int = 100, 
                            pipeline_id: Optional[str] = None, 
                            status: Optional[ExecutionStatus] = None) -> List[Execution]:
        """List executions with pagination and filtering"""
        async with self.connection_pool.acquire() as conn:
            try:
                query = "SELECT * FROM executions"
                params = []
                conditions = []
                
                if pipeline_id:
                    conditions.append(f"pipeline_id = ${len(params) + 1}")
                    params.append(pipeline_id)
                
                if status:
                    conditions.append(f"status = ${len(params) + 1}")
                    params.append(status.value)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += f" ORDER BY created_at DESC OFFSET ${len(params) + 1} LIMIT ${len(params) + 2}"
                params.extend([skip, limit])
                
                rows = await conn.fetch(query, *params)
                return [self._row_to_execution(row) for row in rows]
                
            except Exception as e:
                logger.error(f"Error listing executions: {e}")
                raise
    
    async def update_execution(self, execution_id: str, execution: Execution) -> Optional[Execution]:
        """Update an existing execution"""
        async with self.connection_pool.acquire() as conn:
            try:
                result = await conn.execute("""
                    UPDATE executions 
                    SET status = $2, start_time = $3, end_time = $4, duration = $5,
                        steps = $6, error_message = $7, output_files = $8, logs = $9
                    WHERE id = $1
                """,
                    execution_id,
                    execution.status.value,
                    execution.start_time,
                    execution.end_time,
                    execution.duration,
                    json.dumps([step.dict() for step in execution.steps]),
                    execution.error_message,
                    json.dumps(execution.output_files),
                    json.dumps(execution.logs)
                )
                
                if result == "UPDATE 0":
                    return None
                
                logger.info(f"Updated execution: {execution_id}")
                return execution
                
            except Exception as e:
                logger.error(f"Error updating execution {execution_id}: {e}")
                raise
    
    # File operations
    async def store_file_info(self, file_info: FileInfo) -> FileInfo:
        """Store file information"""
        async with self.connection_pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO file_info (name, path, size, format, uploaded_at, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (path) DO UPDATE SET
                        name = EXCLUDED.name,
                        size = EXCLUDED.size,
                        format = EXCLUDED.format,
                        uploaded_at = EXCLUDED.uploaded_at,
                        metadata = EXCLUDED.metadata
                """,
                    file_info.name,
                    file_info.path,
                    file_info.size,
                    file_info.format.value if file_info.format else None,
                    file_info.uploaded_at,
                    json.dumps(file_info.metadata)
                )
                
                logger.info(f"Stored file info: {file_info.path}")
                return file_info
                
            except Exception as e:
                logger.error(f"Error storing file info: {e}")
                raise
    
    async def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """Get file information"""
        async with self.connection_pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    "SELECT * FROM file_info WHERE path = $1", file_path
                )
                
                if not row:
                    return None
                
                return self._row_to_file_info(row)
                
            except Exception as e:
                logger.error(f"Error getting file info {file_path}: {e}")
                raise
    
    async def list_files(self) -> List[FileInfo]:
        """List all files"""
        async with self.connection_pool.acquire() as conn:
            try:
                rows = await conn.fetch(
                    "SELECT * FROM file_info ORDER BY uploaded_at DESC"
                )
                return [self._row_to_file_info(row) for row in rows]
                
            except Exception as e:
                logger.error(f"Error listing files: {e}")
                raise
    
    async def delete_file_info(self, file_path: str) -> bool:
        """Delete file information"""
        async with self.connection_pool.acquire() as conn:
            try:
                result = await conn.execute(
                    "DELETE FROM file_info WHERE path = $1", file_path
                )
                
                success = result != "DELETE 0"
                if success:
                    logger.info(f"Deleted file info: {file_path}")
                
                return success
                
            except Exception as e:
                logger.error(f"Error deleting file info {file_path}: {e}")
                raise
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        async with self.connection_pool.acquire() as conn:
            try:
                # Count pipelines by status
                pipeline_stats = await conn.fetch(
                    "SELECT status, COUNT(*) as count FROM pipelines GROUP BY status"
                )
                
                # Count executions by status
                execution_stats = await conn.fetch(
                    "SELECT status, COUNT(*) as count FROM executions GROUP BY status"
                )
                
                # Count total files
                file_count = await conn.fetchval("SELECT COUNT(*) FROM file_info")
                
                return {
                    "pipelines": {row['status']: row['count'] for row in pipeline_stats},
                    "executions": {row['status']: row['count'] for row in execution_stats},
                    "files": file_count or 0
                }
                
            except Exception as e:
                logger.error(f"Error getting statistics: {e}")
                raise
    
    def _row_to_pipeline(self, row) -> Pipeline:
        """Convert database row to Pipeline model"""
        from app.models import LoadStep, TransformStep, FilterStep, AggregateStep, JoinStep, SaveStep, ScheduleConfig
        
        # Convert steps from JSON to step objects
        steps = []
        steps_data = json.loads(row['steps']) if row['steps'] else []
        for step_data in steps_data:
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
        if row['schedule']:
            schedule = ScheduleConfig(**json.loads(row['schedule']))
        
        return Pipeline(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            status=PipelineStatus(row['status']),
            steps=steps,
            schedule=schedule,
            metadata=json.loads(row['metadata']) if row['metadata'] else {},
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            created_by=row['created_by']
        )
    
    def _row_to_execution(self, row) -> Execution:
        """Convert database row to Execution model"""
        from app.models import StepExecution
        
        # Convert steps from JSON to step execution objects
        steps = []
        steps_data = json.loads(row['steps']) if row['steps'] else []
        for step_data in steps_data:
            steps.append(StepExecution(**step_data))
        
        return Execution(
            id=row['id'],
            pipeline_id=row['pipeline_id'],
            pipeline_name=row['pipeline_name'],
            status=ExecutionStatus(row['status']),
            start_time=row['start_time'],
            end_time=row['end_time'],
            duration=row['duration'],
            parameters=json.loads(row['parameters']) if row['parameters'] else {},
            triggered_by=row['triggered_by'],
            steps=steps,
            error_message=row['error_message'],
            output_files=json.loads(row['output_files']) if row['output_files'] else [],
            logs=json.loads(row['logs']) if row['logs'] else [],
            created_at=row['created_at']
        )
    
    def _row_to_file_info(self, row) -> FileInfo:
        """Convert database row to FileInfo model"""
        from app.models import DataFormat
        
        format_val = None
        if row['format']:
            try:
                format_val = DataFormat(row['format'])
            except ValueError:
                format_val = None
        
        return FileInfo(
            name=row['name'],
            path=row['path'],
            size=row['size'],
            format=format_val,
            uploaded_at=row['uploaded_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )


# Global database instance
postgres_db = PostgreSQLDatabase()