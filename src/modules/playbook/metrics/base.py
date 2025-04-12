from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import json
import sys
import os

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
    step: Optional[int] = None
    phase: Optional[str] = None

@dataclass
class StepMetrics:
    """Metrics for a single step."""
    session: str
    store_vars: List[str] = field(default_factory=list)
    variable_sizes: Dict[str, int] = field(default_factory=dict)  # Size of stored variables in bytes
    phase: Optional[str] = None
    step: Optional[int] = None

@dataclass
class PhaseMetrics:
    """Metrics for a single phase."""
    name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    parallel: bool = False

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