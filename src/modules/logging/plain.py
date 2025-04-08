import sys
from .base import BaseLogger


class PlainLogger(BaseLogger):
    """Logger that outputs plain text, suitable for CI/file output."""
    
    def __init__(self, log_level: str = "INFO"):
        super().__init__()
        # Configure loguru for plain output
        self.logger.configure(
            handlers=[{
                "sink": sys.stdout,
                "format": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
                "colorize": False,
                "level": log_level
            }]
        )
    
    def log_step(self, step_number: int, method: str, endpoint: str):
        self.logger.info(f"Step {step_number}")
        self.logger.info(f"Method: {method}")
        self.logger.info(f"Endpoint: {endpoint}")

    def log_status(self, status_code: int):
        self.logger.info(f"Status: {status_code}")

    def log_headers(self, headers: dict):
        self.logger.info("Headers:")
        for key, value in headers.items():
            self.logger.info(f"  {key}: {value}")

    def log_body(self, body: str):
        self.logger.info("\nBody:")
        self.logger.info(body)

    def log_error(self, message: str):
        self.logger.error(message)

    def log_warning(self, message: str):
        self.logger.warning(message)

    def log_info(self, message: str):
        self.logger.info(message)

    def log_debug(self, message: str):
        self.logger.debug(message) 