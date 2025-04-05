from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import json
import sys
import os
import psutil

@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    method: str
    endpoint: str
    start_time: datetime
    end_time: datetime
    status_code: int
    duration_ms: float
    success: bool
    error: Optional[str] = None  # Last error encountered
    errors: List[str] = field(default_factory=list)  # All errors encountered during the request
    request_size_bytes: Optional[int] = None  # Size of request payload in bytes
    response_size_bytes: Optional[int] = None  # Size of response payload in bytes
    memory_usage_bytes: Optional[int] = None  # Memory usage during request in bytes
    cpu_percent: Optional[float] = None  # CPU usage during request as percentage

@dataclass
class StepMetrics:
    """Metrics for a single step."""
    session: str
    retry_count: int = 0
    store_vars: List[str] = field(default_factory=list)
    variable_sizes: Dict[str, int] = field(default_factory=dict)  # Size of stored variables in bytes
    memory_usage_bytes: Optional[int] = None  # Memory usage during step in bytes
    cpu_percent: Optional[float] = None  # CPU usage during step as percentage

@dataclass
class PhaseMetrics:
    """Metrics for a single phase."""
    name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    parallel: bool = False
    memory_usage_bytes: Optional[int] = None  # Memory usage during phase in bytes
    cpu_percent: Optional[float] = None  # CPU usage during phase as percentage

@dataclass
class PlaybookMetrics:
    """Metrics for the entire playbook."""
    start_time: datetime
    end_time: datetime
    duration_ms: float
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0.0
    peak_memory_usage_bytes: Optional[int] = None  # Peak memory usage during playbook in bytes
    average_cpu_percent: Optional[float] = None  # Average CPU usage during playbook as percentage
    total_request_size_bytes: Optional[int] = None  # Total size of all request payloads in bytes
    total_response_size_bytes: Optional[int] = None  # Total size of all response payloads in bytes
    total_variable_size_bytes: Optional[int] = None  # Total size of all stored variables in bytes

class MetricsCollector(ABC):
    """Base class for metrics collectors."""
    
    @abstractmethod
    def record_request(self, metrics: RequestMetrics) -> None:
        """Record metrics for a single request."""
        pass
    
    @abstractmethod
    def record_step(self, metrics: StepMetrics) -> None:
        """Record metrics for a single step."""
        pass
    
    @abstractmethod
    def record_phase(self, metrics: PhaseMetrics) -> None:
        """Record metrics for a single phase."""
        pass
    
    @abstractmethod
    def record_playbook(self, metrics: PlaybookMetrics) -> None:
        """Record metrics for the entire playbook."""
        pass
    
    @abstractmethod
    def finalize(self) -> None:
        """Finalize metrics collection."""
        pass
    
    @staticmethod
    def get_memory_usage() -> int:
        """Get current memory usage in bytes."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss  # Return in bytes
    
    @staticmethod
    def get_cpu_usage() -> float:
        """Get current CPU usage as percentage."""
        process = psutil.Process(os.getpid())
        return process.cpu_percent(interval=0.1)
    
    @staticmethod
    def get_object_size(obj: Any) -> int:
        """Get approximate size of an object in bytes."""
        try:
            # Try to get size directly
            return sys.getsizeof(obj)
        except (TypeError, AttributeError):
            # If direct size calculation fails, try JSON serialization
            try:
                return len(json.dumps(obj).encode('utf-8'))
            except (TypeError, OverflowError):
                # If JSON serialization fails, return 0
                return 0 