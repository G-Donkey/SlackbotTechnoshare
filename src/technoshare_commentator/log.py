"""Logging configuration with Rich formatting.

Provides setup_logging() for app initialization and get_logger() for module-level loggers.
"""

import logging
from rich.logging import RichHandler
from .config import get_settings

def setup_logging():
    settings = get_settings()
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    
    # Quiet down some noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)

def get_logger(name: str):
    return logging.getLogger(name)
