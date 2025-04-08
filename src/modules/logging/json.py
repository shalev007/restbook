import json
import sys
from .base import BaseLogger


class JsonLogger(BaseLogger):
    """Logger that outputs JSON for machine parsing."""
    
    def __init__(self, log_level: str = "INFO"):
        super().__init__()
        # Configure loguru for JSON output
        self.logger.configure(
            handlers=[{
                "sink": sys.stdout,
                "serialize": True,  # JSON output
                "format": "{time} | {level} | {message}",
                "level": log_level
            }]
        )
    
    def log_step(self, step_number: int, method: str, endpoint: str):
        self.logger.info("", extra={
            "type": "step",
            "step_number": step_number,
            "method": method,
            "endpoint": endpoint
        })

    def log_status(self, status_code: int):
        self.logger.info("", extra={
            "type": "status",
            "code": status_code
        })

    def log_headers(self, headers: dict):
        self.logger.info("", extra={
            "type": "headers",
            "headers": headers
        })

    def log_body(self, body: str):
        self.logger.info("", extra={
            "type": "body",
            "content": body
        })

    def log_error(self, message: str):
        self.logger.error("", extra={
            "type": "error",
            "message": message
        })

    def log_warning(self, message: str):
        self.logger.warning("", extra={
            "type": "warning",
            "message": message
        })

    def log_info(self, message: str):
        self.logger.info("", extra={
            "type": "info",
            "message": message
        })

    def log_debug(self, message: str):
        self.logger.debug("", extra={
            "type": "debug",
            "message": message
        }) 