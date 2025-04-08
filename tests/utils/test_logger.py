from typing import Dict, List
from src.modules.logging.base import BaseLogger


class _TestLogger(BaseLogger):
    """Test logger that captures all logs."""
    def __init__(self):
        self.logs: List[str] = []
    
    def log_info(self, message: str) -> None:
        self.logs.append(f"INFO: {message}")
    
    def log_error(self, message: str) -> None:
        self.logs.append(f"ERROR: {message}")
    
    def log_status(self, status: int) -> None:
        self.logs.append(f"STATUS: {status}")
    
    def log_body(self, body: str) -> None:
        self.logs.append(f"BODY: {body}")
    
    def log_headers(self, headers: Dict[str, str]) -> None:
        self.logs.append(f"HEADERS: {headers}")
    
    def log_step(self, step_number: int, method: str, endpoint: str) -> None:
        self.logs.append(f"STEP {step_number}: {method} {endpoint}")
    
    def get_logs(self) -> List[str]:
        """Get all captured logs."""
        return self.logs


def create_test_logger() -> BaseLogger:
    """Create a test logger instance."""
    return _TestLogger() 