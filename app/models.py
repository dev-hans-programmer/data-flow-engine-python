"""
Data models for the pipeline system using Pydantic
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


class PipelineStatus(str, Enum):
    """Pipeline status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


class ExecutionStatus(str, Enum):
    """Execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    """Step type enumeration"""
    LOAD = "load"
    TRANSFORM = "transform"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    JOIN = "join"
    SAVE = "save"


class DataFormat(str, Enum):
    """Supported data formats"""
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    XLSX = "xlsx"


class ScheduleType(str, Enum):
    """Schedule type enumeration"""
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"


# Pipeline Step Models
class BaseStep(BaseModel):
    """Base pipeline step"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Step name")
    type: StepType = Field(..., description="Step type")
    description: Optional[str] = Field(None, description="Step description")
    enabled: bool = Field(True, description="Whether step is enabled")
    retry_on_failure: bool = Field(True, description="Retry step on failure")
    max_retries: int = Field(3, description="Maximum retry attempts")


class LoadStep(BaseStep):
    """Data loading step"""
    type: StepType = StepType.LOAD
    source_path: str = Field(..., description="Source file path")
    format: DataFormat = Field(..., description="Data format")
    options: Dict[str, Any] = Field(default_factory=dict, description="Format-specific options")


class TransformStep(BaseStep):
    """Data transformation step"""
    type: StepType = StepType.TRANSFORM
    operations: List[Dict[str, Any]] = Field(..., description="Transformation operations")


class FilterStep(BaseStep):
    """Data filtering step"""
    type: StepType = StepType.FILTER
    conditions: List[Dict[str, Any]] = Field(..., description="Filter conditions")


class AggregateStep(BaseStep):
    """Data aggregation step"""
    type: StepType = StepType.AGGREGATE
    group_by: List[str] = Field(..., description="Columns to group by")
    aggregations: Dict[str, str] = Field(..., description="Aggregation functions")


class JoinStep(BaseStep):
    """Data join step"""
    type: StepType = StepType.JOIN
    right_dataset: str = Field(..., description="Right dataset identifier")
    join_type: str = Field("inner", description="Join type")
    left_on: Union[str, List[str]] = Field(..., description="Left join columns")
    right_on: Union[str, List[str]] = Field(..., description="Right join columns")


class SaveStep(BaseStep):
    """Data saving step"""
    type: StepType = StepType.SAVE
    output_path: str = Field(..., description="Output file path")
    format: DataFormat = Field(..., description="Output format")
    options: Dict[str, Any] = Field(default_factory=dict, description="Format-specific options")


# Schedule Models
class ScheduleConfig(BaseModel):
    """Schedule configuration"""
    type: ScheduleType = Field(..., description="Schedule type")
    start_time: Optional[datetime] = Field(None, description="Schedule start time")
    end_time: Optional[datetime] = Field(None, description="Schedule end time")
    interval: Optional[int] = Field(None, description="Interval for recurring schedules")
    cron_expression: Optional[str] = Field(None, description="Cron expression for cron schedules")
    timezone: str = Field("UTC", description="Timezone for schedule")
    
    @validator('cron_expression')
    def validate_cron(cls, v, values):
        if values.get('type') == ScheduleType.CRON and not v:
            raise ValueError("Cron expression is required for cron schedule type")
        return v


# Pipeline Models
class PipelineCreate(BaseModel):
    """Pipeline creation model"""
    name: str = Field(..., description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    steps: List[Union[LoadStep, TransformStep, FilterStep, AggregateStep, JoinStep, SaveStep]] = Field(
        ..., description="Pipeline steps"
    )
    schedule: Optional[ScheduleConfig] = Field(None, description="Pipeline schedule")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PipelineUpdate(BaseModel):
    """Pipeline update model"""
    name: Optional[str] = Field(None, description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    steps: Optional[List[Union[LoadStep, TransformStep, FilterStep, AggregateStep, JoinStep, SaveStep]]] = Field(
        None, description="Pipeline steps"
    )
    schedule: Optional[ScheduleConfig] = Field(None, description="Pipeline schedule")
    status: Optional[PipelineStatus] = Field(None, description="Pipeline status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class Pipeline(BaseModel):
    """Pipeline model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    status: PipelineStatus = Field(PipelineStatus.DRAFT, description="Pipeline status")
    steps: List[Union[LoadStep, TransformStep, FilterStep, AggregateStep, JoinStep, SaveStep]] = Field(
        ..., description="Pipeline steps"
    )
    schedule: Optional[ScheduleConfig] = Field(None, description="Pipeline schedule")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="Creator user ID")


# Execution Models
class ExecutionCreate(BaseModel):
    """Execution creation model"""
    pipeline_id: str = Field(..., description="Pipeline ID to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters")
    triggered_by: Optional[str] = Field(None, description="Trigger source")


class StepExecution(BaseModel):
    """Step execution details"""
    step_id: str = Field(..., description="Step ID")
    step_name: str = Field(..., description="Step name")
    status: ExecutionStatus = Field(..., description="Step execution status")
    start_time: Optional[datetime] = Field(None, description="Step start time")
    end_time: Optional[datetime] = Field(None, description="Step end time")
    duration: Optional[float] = Field(None, description="Step duration in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retries")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Step output data")


class Execution(BaseModel):
    """Pipeline execution model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_id: str = Field(..., description="Pipeline ID")
    pipeline_name: str = Field(..., description="Pipeline name")
    status: ExecutionStatus = Field(ExecutionStatus.PENDING, description="Execution status")
    start_time: Optional[datetime] = Field(None, description="Execution start time")
    end_time: Optional[datetime] = Field(None, description="Execution end time")
    duration: Optional[float] = Field(None, description="Execution duration in seconds")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters")
    triggered_by: Optional[str] = Field(None, description="Trigger source")
    steps: List[StepExecution] = Field(default_factory=list, description="Step executions")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    output_files: List[str] = Field(default_factory=list, description="Generated output files")
    logs: List[str] = Field(default_factory=list, description="Execution logs")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# File Models
class FileInfo(BaseModel):
    """File information model"""
    name: str = Field(..., description="File name")
    path: str = Field(..., description="File path")
    size: int = Field(..., description="File size in bytes")
    format: Optional[DataFormat] = Field(None, description="File format")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="File metadata")


# Response Models
class PipelineListResponse(BaseModel):
    """Pipeline list response"""
    pipelines: List[Pipeline]
    total: int
    page: int
    size: int


class ExecutionListResponse(BaseModel):
    """Execution list response"""
    executions: List[Execution]
    total: int
    page: int
    size: int


class ApiResponse(BaseModel):
    """Generic API response"""
    success: bool
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
