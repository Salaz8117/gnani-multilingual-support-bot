"""Custom exceptions for the application."""

from typing import Any, Dict, Optional


class GnaniAPIError(Exception):
    """Base exception for Gnani API errors."""
    
    def __init__(
        self,
        message: str,
        service: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.service = service
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(f"[{service}] {message}")


class PrismaError(GnaniAPIError):
    """Prisma STT service errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "Prisma", status_code, response_data)


class EvonError(GnaniAPIError):
    """Evon reasoning service errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "Evon", status_code, response_data)


class TimbreError(GnaniAPIError):
    """Timbre TTS service errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "Timbre", status_code, response_data)


class AudioProcessingError(Exception):
    """Audio processing errors."""
    
    def __init__(self, message: str, audio_path: Optional[str] = None):
        self.message = message
        self.audio_path = audio_path
        super().__init__(f"Audio processing error: {message}")


class ConfigurationError(Exception):
    """Configuration errors."""
    
    def __init__(self, message: str, missing_keys: Optional[list[str]] = None):
        self.message = message
        self.missing_keys = missing_keys or []
        super().__init__(f"Configuration error: {message}")


class PipelineError(Exception):
    """Pipeline orchestration errors."""
    
    def __init__(self, message: str, stage: str, original_error: Optional[Exception] = None):
        self.message = message
        self.stage = stage
        self.original_error = original_error
        super().__init__(f"Pipeline error at {stage}: {message}")