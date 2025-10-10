"""
Logging configuration for Gallery Twin application.
Provides structured logging with different levels and contexts.
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from typing import Any, Dict


def setup_logging(level: str = "INFO", log_file: str = "logs/gallery.log") -> None:
    """
    Setup structured logging for Gallery Twin.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (will create directory if needed)
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)

    # Create formatter for structured logs
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Setup handlers
    handlers = [
        logging.StreamHandler(sys.stdout),
    ]

    # Add file handler with rotation
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,  # Override any existing configuration
    )

    # Set log levels for noisy libraries
    # INFO level for sqlalchemy.engine to see DB connections and basic operations
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


# Logger instances for different modules
logger = logging.getLogger("gallery_twin")
db_logger = logging.getLogger("gallery_twin.database")
auth_logger = logging.getLogger("gallery_twin.auth")
session_logger = logging.getLogger("gallery_twin.session")
content_logger = logging.getLogger("gallery_twin.content")
request_logger = logging.getLogger("gallery_twin.request")


def log_request(request, status_code: int):
    """Log incoming HTTP requests."""
    request_logger.debug(
        f"{request.method} {request.url.path} | STATUS={status_code} | IP={request.client.host}"
    )


def log_session_event(
    event_type: str, session_uuid: str, level: str = "INFO", **kwargs
) -> None:
    """Log session-related events with structured data."""
    extra_data = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    log_func = getattr(session_logger, level.lower(), session_logger.info)
    log_func(f"{event_type} | session={session_uuid} | {extra_data}")


def log_answer_submission(
    session_uuid: str,
    question_id: int,
    exhibit_slug: str = None,
    level: str = "DEBUG",
    **kwargs,
) -> None:
    """Log answer submission events."""
    extra_data = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(
        f"ANSWER_SUBMITTED | session={session_uuid} | question_id={question_id} | exhibit={exhibit_slug} | {extra_data}"
    )


def log_admin_access(
    username: str, action: str, level: str = "INFO", **kwargs
) -> None:
    """Log admin access and actions."""
    extra_data = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    log_func = getattr(auth_logger, level.lower(), auth_logger.info)
    log_func(f"ADMIN_ACCESS | user={username} | action={action} | {extra_data}")


def log_content_loading(
    files_processed: int, level: str = "INFO", **kwargs
) -> None:
    """Log content loading operations."""
    extra_data = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    log_func = getattr(content_logger, level.lower(), content_logger.info)
    log_func(f"CONTENT_LOADED | files={files_processed} | {extra_data}")


def log_error(error_type: str, message: str, **kwargs) -> None:
    """Log application errors with context."""
    extra_data = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.error(f"{error_type} | {message} | {extra_data}")


# Initialize logging when module is imported
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", "logs/gallery.log"),
)
