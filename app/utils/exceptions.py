"""
Custom exceptions for the pipeline system
"""


class PipelineSystemError(Exception):
    """Base exception for pipeline system errors"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class PipelineExecutionError(PipelineSystemError):
    """Raised when pipeline execution fails"""
    pass


class StepExecutionError(PipelineSystemError):
    """Raised when a pipeline step fails"""
    pass


class DataProcessingError(PipelineSystemError):
    """Raised when data processing operations fail"""
    pass


class ValidationError(PipelineSystemError):
    """Raised when validation fails"""
    pass


class FileNotFoundError(PipelineSystemError):
    """Raised when a required file is not found"""
    pass


class UnsupportedFormatError(PipelineSystemError):
    """Raised when an unsupported data format is used"""
    pass


class ConfigurationError(PipelineSystemError):
    """Raised when configuration is invalid"""
    pass


class SchedulingError(PipelineSystemError):
    """Raised when scheduling operations fail"""
    pass


class DatabaseError(PipelineSystemError):
    """Raised when database operations fail"""
    pass


class AuthenticationError(PipelineSystemError):
    """Raised when authentication fails"""
    pass


class AuthorizationError(PipelineSystemError):
    """Raised when authorization fails"""
    pass


class ResourceLimitError(PipelineSystemError):
    """Raised when resource limits are exceeded"""
    pass


class TimeoutError(PipelineSystemError):
    """Raised when operations timeout"""
    pass


class NetworkError(PipelineSystemError):
    """Raised when network operations fail"""
    pass


class ExternalServiceError(PipelineSystemError):
    """Raised when external service calls fail"""
    pass
