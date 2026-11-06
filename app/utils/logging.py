"""Structured logging configuration."""

import sys
from typing import Optional

import structlog

from app.core.config import get_settings


def configure_logging():
    """Configure structured logging for the application."""
    settings = get_settings()
    
    log_level = settings.log_level.upper()
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer(colors=True) if settings.debug 
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None):
    """Get a structured logger instance."""
    return structlog.get_logger(name)