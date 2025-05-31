"""
Configuration settings for the Data Processing Pipeline System
"""

import os
from typing import List
from pydantic_settings import BaseSettings


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
    
    # PostgreSQL Database settings
    # Option 1: Use DATABASE_URL (if provided)
    database_url: str = os.getenv("DATABASE_URL", "")
    
    # Option 2: Use individual connection parameters
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "pipeline_system")
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "")
    
    @property
    def get_database_url(self) -> str:
        """Get the database URL, either from DATABASE_URL or constructed from individual parameters"""
        if self.database_url:
            return self.database_url
        else:
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Scheduler settings
    scheduler_check_interval: int = 60  # Check every minute
    
    class Config:
        env_file = ".env"


settings = Settings()
