from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

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
    error: Optional[str] = None

@dataclass
class StepMetrics:
    """Metrics for a single step."""
    session: str
    request: RequestMetrics
    retry_count: int = 0
    store_vars: Optional[List[str]] = None

@dataclass
class PhaseMetrics:
    """Metrics for a single phase."""
    name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    steps: List[StepMetrics]
    parallel: bool = False

@dataclass
class PlaybookMetrics:
    """Overall metrics for the playbook execution."""
    start_time: datetime
    end_time: datetime
    duration_ms: float
    phases: List[PhaseMetrics]
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration_ms: float

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
        """Record overall playbook metrics."""
        pass
    
    @abstractmethod
    def finalize(self) -> None:
        """Finalize and save all collected metrics."""
        pass 