from abc import ABC, abstractmethod


class BaseLogger(ABC):
    """Abstract base class for loggers."""
    
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
    def log_info(self, message: str):
        """Log an info message."""
        pass 