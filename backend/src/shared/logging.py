import logging
import json
import time
from contextvars import ContextVar
from typing import Any

# Context variables for request-scoped logging details
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")
employee_id_ctx: ContextVar[str] = ContextVar("employee_id", default="")

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno,
            "correlationId": correlation_id_ctx.get(),
            "employeeId": employee_id_ctx.get(),
        }

        # Handle operation/context attributes if added to log
        if hasattr(record, "operation"):
            log_data["operation"] = getattr(record, "operation")
        if hasattr(record, "extra_context"):
            log_data["context"] = getattr(record, "extra_context")
            
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            # ISO 8601 UTC format by default
            s = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created))
        return s

def setup_logger(log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("app")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    # Prevent propagation to the root logger to avoid raw print duplication
    logger.propagate = False
    return logger

# Initialize logger
from src.config.settings import settings
logger = setup_logger(settings.log_level)
