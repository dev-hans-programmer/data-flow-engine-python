"""
SQLAlchemy database models for the pipeline system
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Float, JSON, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.models import PipelineStatus, ExecutionStatus, StepType, DataFormat

Base = declarative_base()


class Pipeline(Base):
    """Pipeline database model"""
    __tablename__ = "pipelines"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(Enum(PipelineStatus), default=PipelineStatus.DRAFT)
    steps = Column(JSON, nullable=False)  # Store pipeline steps as JSON
    schedule = Column(JSON)  # Store schedule configuration as JSON
    pipeline_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String)
    
    # Relationships
    executions = relationship("Execution", back_populates="pipeline")


class Execution(Base):
    """Pipeline execution database model"""
    __tablename__ = "executions"
    
    id = Column(String, primary_key=True)
    pipeline_id = Column(String, ForeignKey("pipelines.id"), nullable=False)
    pipeline_name = Column(String, nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Float)
    parameters = Column(JSON, default=dict)
    triggered_by = Column(String)
    steps = Column(JSON, default=list)  # Store step executions as JSON
    error_message = Column(Text)
    output_files = Column(JSON, default=list)
    logs = Column(JSON, default=list)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    pipeline = relationship("Pipeline", back_populates="executions")


class FileInfo(Base):
    """File information database model"""
    __tablename__ = "file_info"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False, unique=True)
    size = Column(Integer, nullable=False)
    format = Column(Enum(DataFormat))
    uploaded_at = Column(DateTime, default=func.now())
    metadata = Column(JSON, default=dict)


class ApiSource(Base):
    """API source configuration database model"""
    __tablename__ = "api_sources"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    method = Column(String, default="GET")
    headers = Column(JSON, default=dict)
    params = Column(JSON, default=dict)
    auth_config = Column(JSON, default=dict)
    polling_interval = Column(Integer, default=300)  # seconds
    is_active = Column(Boolean, default=True)
    last_fetch = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    metadata = Column(JSON, default=dict)


class WebhookConfig(Base):
    """Webhook configuration database model"""
    __tablename__ = "webhook_configs"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    endpoint_path = Column(String, nullable=False, unique=True)
    auth_token = Column(String)
    expected_headers = Column(JSON, default=dict)
    data_mapping = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    metadata = Column(JSON, default=dict)


class TriggerConfig(Base):
    """File/event trigger configuration database model"""
    __tablename__ = "trigger_configs"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    trigger_type = Column(String, nullable=False)  # 'file', 'webhook', 'schedule'
    config = Column(JSON, nullable=False)  # Configuration specific to trigger type
    pipeline_id = Column(String, ForeignKey("pipelines.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    metadata = Column(JSON, default=dict)