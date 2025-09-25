"""Service logging configuration for TACoreService."""

import os
import logging
import logging.handlers
from typing import Optional
from ..config import get_settings


class ServiceLogger:
    """Centralized logging configuration for TACoreService."""

    def __init__(self):
        self.settings = get_settings()
        self._configured = False

    def setup_logging(self, log_level: Optional[str] = None):
        """Setup logging configuration for the service."""
        if self._configured:
            return

        # Determine log level
        if log_level:
            level = getattr(logging, log_level.upper(), logging.INFO)
        elif self.settings.debug:
            level = logging.DEBUG
        else:
            level = logging.INFO

        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )

        simple_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)

        # File handler for general logs
        general_log_file = os.path.join(log_dir, "tacoreservice.log")
        file_handler = logging.handlers.RotatingFileHandler(
            general_log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        # Error log file
        error_log_file = os.path.join(log_dir, "tacoreservice_errors.log")
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)

        # Request log file
        request_log_file = os.path.join(log_dir, "tacoreservice_requests.log")
        request_handler = logging.handlers.RotatingFileHandler(
            request_log_file, maxBytes=50 * 1024 * 1024, backupCount=10  # 50MB
        )
        request_handler.setLevel(logging.INFO)
        request_handler.setFormatter(detailed_formatter)

        # Create request logger
        request_logger = logging.getLogger("tacoreservice.requests")
        request_logger.addHandler(request_handler)
        request_logger.setLevel(logging.INFO)
        request_logger.propagate = False  # Don't propagate to root logger

        # Worker log file
        worker_log_file = os.path.join(log_dir, "tacoreservice_workers.log")
        worker_handler = logging.handlers.RotatingFileHandler(
            worker_log_file, maxBytes=20 * 1024 * 1024, backupCount=5  # 20MB
        )
        worker_handler.setLevel(logging.INFO)
        worker_handler.setFormatter(detailed_formatter)

        # Create worker logger
        worker_logger = logging.getLogger("tacoreservice.workers")
        worker_logger.addHandler(worker_handler)
        worker_logger.setLevel(logging.INFO)
        worker_logger.propagate = False

        # Performance log file
        performance_log_file = os.path.join(log_dir, "tacoreservice_performance.log")
        performance_handler = logging.handlers.RotatingFileHandler(
            performance_log_file, maxBytes=20 * 1024 * 1024, backupCount=5  # 20MB
        )
        performance_handler.setLevel(logging.INFO)
        performance_formatter = logging.Formatter("%(asctime)s - %(message)s")
        performance_handler.setFormatter(performance_formatter)

        # Create performance logger
        performance_logger = logging.getLogger("tacoreservice.performance")
        performance_logger.addHandler(performance_handler)
        performance_logger.setLevel(logging.INFO)
        performance_logger.propagate = False

        self._configured = True

        # Log configuration completion
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured - Level: {logging.getLevelName(level)}")
        logger.info(f"Log directory: {log_dir}")

    @staticmethod
    def get_request_logger() -> logging.Logger:
        """Get the request logger."""
        return logging.getLogger("tacoreservice.requests")

    @staticmethod
    def get_worker_logger() -> logging.Logger:
        """Get the worker logger."""
        return logging.getLogger("tacoreservice.workers")

    @staticmethod
    def get_performance_logger() -> logging.Logger:
        """Get the performance logger."""
        return logging.getLogger("tacoreservice.performance")

    @staticmethod
    def log_request(
        request_id: str,
        method: str,
        client_id: str,
        worker_id: str,
        processing_time_ms: int,
        status: str,
    ):
        """Log a request with structured format."""
        request_logger = ServiceLogger.get_request_logger()
        request_logger.info(
            f"REQUEST | ID: {request_id} | METHOD: {method} | CLIENT: {client_id} | "
            f"WORKER: {worker_id} | TIME: {processing_time_ms}ms | STATUS: {status}"
        )

    @staticmethod
    def log_worker_event(worker_id: str, event: str, details: str = ""):
        """Log a worker event."""
        worker_logger = ServiceLogger.get_worker_logger()
        worker_logger.info(
            f"WORKER | ID: {worker_id} | EVENT: {event} | DETAILS: {details}"
        )

    @staticmethod
    def log_performance_metric(
        metric_name: str, value: float, unit: str = "", context: str = ""
    ):
        """Log a performance metric."""
        performance_logger = ServiceLogger.get_performance_logger()
        performance_logger.info(
            f"METRIC | NAME: {metric_name} | VALUE: {value} | UNIT: {unit} | CONTEXT: {context}"
        )

    @staticmethod
    def log_error_with_context(
        logger: logging.Logger,
        error: Exception,
        context: str = "",
        request_id: str = "",
    ):
        """Log an error with additional context."""
        error_msg = f"ERROR | TYPE: {type(error).__name__} | MESSAGE: {str(error)}"

        if request_id:
            error_msg += f" | REQUEST_ID: {request_id}"

        if context:
            error_msg += f" | CONTEXT: {context}"

        logger.error(error_msg, exc_info=True)

    def get_log_files_info(self) -> dict:
        """Get information about log files."""
        log_dir = os.path.join(os.getcwd(), "logs")
        log_files = [
            "tacoreservice.log",
            "tacoreservice_errors.log",
            "tacoreservice_requests.log",
            "tacoreservice_workers.log",
            "tacoreservice_performance.log",
        ]

        files_info = {}

        for log_file in log_files:
            file_path = os.path.join(log_dir, log_file)
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                files_info[log_file] = {
                    "path": file_path,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified_time": stat.st_mtime,
                }
            else:
                files_info[log_file] = {"path": file_path, "exists": False}

        return files_info


# Global logger instance
_service_logger = ServiceLogger()


def setup_logging(log_level: Optional[str] = None):
    """Setup logging for the service."""
    _service_logger.setup_logging(log_level)


def get_request_logger() -> logging.Logger:
    """Get the request logger."""
    return ServiceLogger.get_request_logger()


def get_worker_logger() -> logging.Logger:
    """Get the worker logger."""
    return ServiceLogger.get_worker_logger()


def get_performance_logger() -> logging.Logger:
    """Get the performance logger."""
    return ServiceLogger.get_performance_logger()


def log_request(
    request_id: str,
    method: str,
    client_id: str,
    worker_id: str,
    processing_time_ms: int,
    status: str,
):
    """Log a request with structured format."""
    ServiceLogger.log_request(
        request_id, method, client_id, worker_id, processing_time_ms, status
    )


def log_worker_event(worker_id: str, event: str, details: str = ""):
    """Log a worker event."""
    ServiceLogger.log_worker_event(worker_id, event, details)


def log_performance_metric(
    metric_name: str, value: float, unit: str = "", context: str = ""
):
    """Log a performance metric."""
    ServiceLogger.log_performance_metric(metric_name, value, unit, context)


def log_error_with_context(
    logger: logging.Logger, error: Exception, context: str = "", request_id: str = ""
):
    """Log an error with additional context."""
    ServiceLogger.log_error_with_context(logger, error, context, request_id)
