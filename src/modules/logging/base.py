from abc import ABC, abstractmethod
from loguru import logger


class BaseLogger(ABC):
    """Abstract base class for loggers."""
    
    def __init__(self, log_level: str = "INFO"):
        self.logger = logger
        self.log_level = log_level
    
    @abstractmethod
    def log_step(self, step_number: int, method: str, endpoint: str):
        """Log a step execution."""
        pass

    @abstractmethod
    def log_status(self, status_code: int):
        """Log a response status code."""
        pass

    @abstractmethod
    def log_headers(self, headers: dict):
        """Log response headers."""
        pass

    @abstractmethod
    def log_body(self, body: str):
        """Log response body."""
        pass

    @abstractmethod
    def log_error(self, message: str):
        """Log an error message."""
        pass

    @abstractmethod
    def log_warning(self, message: str):
        """Log a warning message."""
        pass

    @abstractmethod
    def log_info(self, message: str):
        """Log an info message."""
        pass

    @abstractmethod
    def log_debug(self, message: str):
        """Log a debug message."""
        pass 