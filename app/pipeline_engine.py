"""
Pipeline execution engine for processing data workflows
"""

import asyncio
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

from app.models import (
    Pipeline, Execution, StepExecution, ExecutionStatus,
    LoadStep, TransformStep, FilterStep, AggregateStep, JoinStep, SaveStep,
    DataFormat
)
from app.data_processor import DataProcessor
from app.postgres_db import postgres_db as db
from app.utils.logger import get_logger
from app.utils.exceptions import PipelineExecutionError, StepExecutionError
from config import settings

logger = get_logger(__name__)


class PipelineEngine:
    """Main pipeline execution engine"""
    
    def __init__(self):
        self.data_processor = DataProcessor()
        self.running_executions: Dict[str, asyncio.Task] = {}
        self.execution_semaphore = asyncio.Semaphore(settings.max_concurrent_executions)
    
    async def execute_pipeline(self, pipeline: Pipeline, parameters: Dict[str, Any] = None) -> Execution:
        """Execute a pipeline asynchronously"""
        if parameters is None:
            parameters = {}
        
        # Create execution record
        execution = Execution(
            pipeline_id=pipeline.id,
            pipeline_name=pipeline.name,
            parameters=parameters,
            triggered_by="manual"
        )
        
        # Store execution in database
        await db.create_execution(execution)
        
        # Start execution task
        task = asyncio.create_task(self._execute_pipeline_task(execution, pipeline))
        self.running_executions[execution.id] = task
        
        logger.info(f"Started pipeline execution: {execution.id}")
        return execution
    
    async def _execute_pipeline_task(self, execution: Execution, pipeline: Pipeline):
        """Execute pipeline in a background task"""
        async with self.execution_semaphore:
            try:
                await self._run_pipeline(execution, pipeline)
            except Exception as e:
                logger.error(f"Pipeline execution failed: {execution.id} - {e}")
                await self._handle_execution_error(execution, str(e))
            finally:
                # Remove from running executions
                self.running_executions.pop(execution.id, None)
    
    async def _run_pipeline(self, execution: Execution, pipeline: Pipeline):
        """Run the actual pipeline execution"""
        execution.status = ExecutionStatus.RUNNING
        execution.start_time = datetime.utcnow()
        await db.update_execution(execution.id, execution)
        
        # Execution context to store intermediate data
        context = {
            "datasets": {},  # Store datasets by name
            "variables": execution.parameters.copy(),  # Store variables
            "execution_id": execution.id,
            "pipeline_id": pipeline.id
        }
        
        try:
            # Execute each step
            for step in pipeline.steps:
                if not step.enabled:
                    logger.info(f"Skipping disabled step: {step.name}")
                    continue
                
                step_execution = StepExecution(
                    step_id=step.id,
                    step_name=step.name,
                    status=ExecutionStatus.RUNNING,
                    start_time=datetime.utcnow()
                )
                
                execution.steps.append(step_execution)
                await db.update_execution(execution.id, execution)
                
                try:
                    await self._execute_step(step, context, step_execution)
                    step_execution.status = ExecutionStatus.COMPLETED
                    step_execution.end_time = datetime.utcnow()
                    step_execution.duration = (step_execution.end_time - step_execution.start_time).total_seconds()
                    
                except Exception as e:
                    await self._handle_step_error(step, step_execution, str(e), context)
                    if not step.retry_on_failure or step_execution.retry_count >= step.max_retries:
                        raise StepExecutionError(f"Step {step.name} failed: {e}")
                
                await db.update_execution(execution.id, execution)
            
            # Mark execution as completed
            execution.status = ExecutionStatus.COMPLETED
            execution.end_time = datetime.utcnow()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            logger.info(f"Pipeline execution completed: {execution.id}")
            
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.end_time = datetime.utcnow()
            if execution.start_time:
                execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            logger.error(f"Pipeline execution failed: {execution.id} - {e}")
            raise
        
        finally:
            await db.update_execution(execution.id, execution)
    
    async def _execute_step(self, step: Any, context: Dict[str, Any], step_execution: StepExecution):
        """Execute a single pipeline step"""
        logger.info(f"Executing step: {step.name} ({step.type})")
        
        try:
            if isinstance(step, LoadStep):
                await self._execute_load_step(step, context, step_execution)
            elif isinstance(step, TransformStep):
                await self._execute_transform_step(step, context, step_execution)
            elif isinstance(step, FilterStep):
                await self._execute_filter_step(step, context, step_execution)
            elif isinstance(step, AggregateStep):
                await self._execute_aggregate_step(step, context, step_execution)
            elif isinstance(step, JoinStep):
                await self._execute_join_step(step, context, step_execution)
            elif isinstance(step, SaveStep):
                await self._execute_save_step(step, context, step_execution)
            else:
                raise StepExecutionError(f"Unknown step type: {step.type}")
                
        except Exception as e:
            logger.error(f"Step execution error: {step.name} - {e}")
            step_execution.error_message = str(e)
            raise
    
    async def _execute_load_step(self, step: LoadStep, context: Dict[str, Any], step_execution: StepExecution):
        """Execute a data loading step"""
        file_path = Path(step.source_path)
        if not file_path.is_absolute() and not str(file_path).startswith(settings.upload_directory):
            file_path = Path(settings.upload_directory) / file_path
        
        if not file_path.exists():
            raise StepExecutionError(f"Source file not found: {file_path}")
        
        # Load data using data processor
        df = await self.data_processor.load_data(str(file_path), step.format, step.options)
        
        # Store in context with step name as key
        context["datasets"][step.name] = df
        
        step_execution.output_data = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns)
        }
        
        logger.info(f"Loaded data: {len(df)} rows, {len(df.columns)} columns")
    
    async def _execute_transform_step(self, step: TransformStep, context: Dict[str, Any], step_execution: StepExecution):
        """Execute a data transformation step"""
        # Get the main dataset (assume first loaded dataset if not specified)
        dataset_name = step.operations[0].get("dataset", list(context["datasets"].keys())[0])
        df = context["datasets"][dataset_name].copy()
        
        # Apply transformations
        for operation in step.operations:
            df = await self.data_processor.apply_transformation(df, operation)
        
        # Store result
        context["datasets"][step.name] = df
        
        step_execution.output_data = {
            "rows": len(df),
            "columns": len(df.columns),
            "operations_applied": len(step.operations)
        }
    
    async def _execute_filter_step(self, step: FilterStep, context: Dict[str, Any], step_execution: StepExecution):
        """Execute a data filtering step"""
        # Get the dataset to filter
        dataset_name = step.conditions[0].get("dataset", list(context["datasets"].keys())[0])
        df = context["datasets"][dataset_name].copy()
        
        original_rows = len(df)
        
        # Apply filters
        for condition in step.conditions:
            df = await self.data_processor.apply_filter(df, condition)
        
        # Store result
        context["datasets"][step.name] = df
        
        step_execution.output_data = {
            "original_rows": original_rows,
            "filtered_rows": len(df),
            "rows_removed": original_rows - len(df),
            "conditions_applied": len(step.conditions)
        }
    
    async def _execute_aggregate_step(self, step: AggregateStep, context: Dict[str, Any], step_execution: StepExecution):
        """Execute a data aggregation step"""
        # Get the dataset to aggregate
        dataset_name = list(context["datasets"].keys())[0]  # Use first dataset if not specified
        df = context["datasets"][dataset_name].copy()
        
        # Perform aggregation
        result_df = await self.data_processor.aggregate_data(df, step.group_by, step.aggregations)
        
        # Store result
        context["datasets"][step.name] = result_df
        
        step_execution.output_data = {
            "original_rows": len(df),
            "aggregated_rows": len(result_df),
            "group_columns": step.group_by,
            "aggregations": step.aggregations
        }
    
    async def _execute_join_step(self, step: JoinStep, context: Dict[str, Any], step_execution: StepExecution):
        """Execute a data join step"""
        # Get datasets
        left_dataset_name = list(context["datasets"].keys())[0]  # Use first dataset as left
        left_df = context["datasets"][left_dataset_name].copy()
        right_df = context["datasets"][step.right_dataset].copy()
        
        # Perform join
        result_df = await self.data_processor.join_data(
            left_df, right_df, step.left_on, step.right_on, step.join_type
        )
        
        # Store result
        context["datasets"][step.name] = result_df
        
        step_execution.output_data = {
            "left_rows": len(left_df),
            "right_rows": len(right_df),
            "result_rows": len(result_df),
            "join_type": step.join_type
        }
    
    async def _execute_save_step(self, step: SaveStep, context: Dict[str, Any], step_execution: StepExecution):
        """Execute a data saving step"""
        # Get the dataset to save
        dataset_name = list(context["datasets"].keys())[-1]  # Use last dataset if not specified
        df = context["datasets"][dataset_name].copy()
        
        # Prepare output path
        output_path = Path(step.output_path)
        if not output_path.is_absolute() and not str(output_path).startswith(settings.output_directory):
            output_path = Path(settings.output_directory) / output_path
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save data
        await self.data_processor.save_data(df, str(output_path), step.format, step.options)
        
        step_execution.output_data = {
            "output_path": str(output_path),
            "rows_saved": len(df),
            "columns_saved": len(df.columns),
            "format": step.format
        }
        
        # Add to execution output files
        execution = await db.get_execution(context["execution_id"])
        if execution:
            execution.output_files.append(str(output_path))
            await db.update_execution(execution.id, execution)
    
    async def _handle_step_error(self, step: Any, step_execution: StepExecution, error: str, context: Dict[str, Any]):
        """Handle step execution error with retry logic"""
        step_execution.error_message = error
        step_execution.retry_count += 1
        step_execution.status = ExecutionStatus.FAILED
        
        if step.retry_on_failure and step_execution.retry_count < step.max_retries:
            logger.info(f"Retrying step {step.name} (attempt {step_execution.retry_count + 1})")
            
            # Wait before retry
            await asyncio.sleep(settings.retry_delay)
            
            # Reset step execution for retry
            step_execution.status = ExecutionStatus.RUNNING
            step_execution.start_time = datetime.utcnow()
            step_execution.error_message = None
            
            # Retry the step
            try:
                await self._execute_step(step, context, step_execution)
                step_execution.status = ExecutionStatus.COMPLETED
                step_execution.end_time = datetime.utcnow()
                step_execution.duration = (step_execution.end_time - step_execution.start_time).total_seconds()
            except Exception as retry_error:
                await self._handle_step_error(step, step_execution, str(retry_error), context)
    
    async def _handle_execution_error(self, execution: Execution, error: str):
        """Handle pipeline execution error"""
        execution.status = ExecutionStatus.FAILED
        execution.error_message = error
        execution.end_time = datetime.utcnow()
        
        if execution.start_time:
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
        
        await db.update_execution(execution.id, execution)
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution"""
        if execution_id in self.running_executions:
            task = self.running_executions[execution_id]
            task.cancel()
            
            # Update execution status
            execution = await db.get_execution(execution_id)
            if execution:
                execution.status = ExecutionStatus.CANCELLED
                execution.end_time = datetime.utcnow()
                if execution.start_time:
                    execution.duration = (execution.end_time - execution.start_time).total_seconds()
                await db.update_execution(execution_id, execution)
            
            logger.info(f"Cancelled execution: {execution_id}")
            return True
        
        return False
    
    async def get_running_executions(self) -> List[str]:
        """Get list of currently running execution IDs"""
        return list(self.running_executions.keys())
    
    async def cleanup_completed_tasks(self):
        """Clean up completed execution tasks"""
        completed_tasks = []
        for execution_id, task in self.running_executions.items():
            if task.done():
                completed_tasks.append(execution_id)
        
        for execution_id in completed_tasks:
            self.running_executions.pop(execution_id, None)


# Global pipeline engine instance
engine = PipelineEngine()
