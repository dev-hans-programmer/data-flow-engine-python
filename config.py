"""
Configuration settings for the Data Processing Pipeline System
"""

import os
from typing import List
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application settings
    app_name: str = "Data Processing Pipeline System"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # File settings
    upload_directory: str = "uploads"
    output_directory: str = "outputs"
    logs_directory: str = "logs"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_file_types: List[str] = [".csv", ".json", ".parquet", ".xlsx"]
    
    # Pipeline settings
    max_concurrent_executions: int = 5
    execution_timeout: int = 3600  # 1 hour
    retry_attempts: int = 3
    retry_delay: int = 60  # 60 seconds
    
    # Database settings (in-memory for this implementation)
    database_url: str = "sqlite:///./pipelines.db"
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Scheduler settings
    scheduler_check_interval: int = 60  # Check every minute
    
    class Config:
        env_file = ".env"


settings = Settings()
