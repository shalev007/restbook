"""Metrics observer implementation."""
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field

from src.modules.playbook.metrics.base import MetricsCollector
from src.modules.playbook.metrics.base import (
    RequestMetrics, StepMetrics, PhaseMetrics, PlaybookMetrics
)
from src.modules.playbook.observer.base import ExecutionObserver
from src.modules.playbook.observer.events import (
    PlaybookStartEvent, PlaybookEndEvent,
    PhaseStartEvent, PhaseEndEvent,
    StepStartEvent, StepEndEvent,
    RequestStartEvent, RequestEndEvent
)


@dataclass
class RequestCounters:
    """Tracks request-related counts."""
    total: int = 0
    successful: int = 0
    failed: int = 0
    total_request_size: int = 0
    total_response_size: int = 0
    total_variable_size: int = 0

@dataclass
class PlaybookContext:
    """Tracks playbook-level context."""
    start_time: datetime

@dataclass
class PhaseContext:
    """Tracks phase-level context."""
    id: str
    name: str
    start_time: datetime
    step_ids: Set[str] = field(default_factory=set)

@dataclass
class StepContext:
    """Tracks step-level context."""
    id: str
    step_index: int
    session: str
    start_time: datetime
    phase_id: str
    request_ids: Set[str] = field(default_factory=set)

@dataclass
class RequestContext:
    """Tracks request-level context."""
    id: str
    method: str
    endpoint: str
    start_time: datetime
    step_id: str

    def end(self, 
            end_time: datetime,
            status_code: int,
            success: bool,
            error: Optional[str] = None,
            errors: Optional[List[str]] = None,
            request_size_bytes: Optional[int] = None,
            response_size_bytes: Optional[int] = None) -> RequestMetrics:
        """Create RequestMetrics from this context."""
        duration_ms = (end_time - self.start_time).total_seconds() * 1000
        
        # Convert step_id to step number if available
        step_number = None
        if self.step_id:
            try:
                step_number = int(self.step_id.split('-')[-1])
            except (ValueError, IndexError):
                pass
        
        return RequestMetrics(
            method=self.method,
            endpoint=self.endpoint,
            start_time=self.start_time,
            end_time=end_time,
            status_code=status_code,
            duration_ms=duration_ms,
            success=success,
            error=error,
            errors=errors or [],
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
            step=step_number
        )

class MetricsObserver(ExecutionObserver):
    """Metrics-specific implementation of execution observer."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.collector = metrics_collector
        
        # Active execution contexts
        self._active_playbook: Optional[PlaybookContext] = None
        self._active_phases: Dict[str, PhaseContext] = {}
        self._active_steps: Dict[str, StepContext] = {}
        self._active_requests: Dict[str, RequestContext] = {}
        
        # Counters
        self._request_counts = RequestCounters()
    
    def get_object_size(self, obj: Any) -> int:
        """Get size of an object in bytes."""
        return self.collector.get_object_size(obj)
    
    def on_playbook_start(self, event: PlaybookStartEvent) -> None:
        """Handle playbook start event."""
        self._active_playbook = PlaybookContext(
            start_time=event.timestamp
        )
    
    def on_playbook_end(self, event: PlaybookEndEvent) -> None:
        """Handle playbook end event."""
        if self._active_playbook is None:
            return
            
        # Record playbook metrics
        playbook_duration_ms = (event.timestamp - self._active_playbook.start_time).total_seconds() * 1000
        
        playbook_metrics = PlaybookMetrics(
            start_time=self._active_playbook.start_time,
            end_time=event.timestamp,
            duration_ms=playbook_duration_ms,
            total_requests=self._request_counts.total,
            successful_requests=self._request_counts.successful,
            failed_requests=self._request_counts.failed,
            total_duration_ms=playbook_duration_ms,
            total_request_size_bytes=self._request_counts.total_request_size,
            total_response_size_bytes=self._request_counts.total_response_size,
            total_variable_size_bytes=self._request_counts.total_variable_size
        )
        
        self.collector.record_playbook(playbook_metrics)
        self.collector.finalize()
    
    def on_phase_start(self, event: PhaseStartEvent) -> None:
        """Handle phase start event."""
        context = PhaseContext(
            id=event.id,
            name=event.phase_name,
            start_time=event.timestamp
        )
        self._active_phases[event.id] = context
    
    def on_phase_end(self, event: PhaseEndEvent) -> None:
        """Handle phase end event."""
        phase = self._active_phases.pop(event.id)
        
        # Create metrics
        metrics = PhaseMetrics(
            name=phase.name,
            start_time=phase.start_time,
            end_time=event.timestamp,
            duration_ms=(event.timestamp - phase.start_time).total_seconds() * 1000,
            parallel=event.parallel
        )
        
        self.collector.record_phase(metrics)
    
    def on_step_start(self, event: StepStartEvent) -> None:
        """Handle step start event."""
        context = StepContext(
            id=event.id,
            step_index=event.step_index,
            session=event.session,
            start_time=event.timestamp,
            phase_id=event.phase_id
        )
        self._active_steps[event.id] = context
    
    def on_step_end(self, event: StepEndEvent) -> None:
        """Handle step end event."""
        step = self._active_steps.pop(event.id)
        phase = self._active_phases[step.phase_id]
        
        # Calculate variable sizes
        variable_sizes = {}
        var_names = []
        for store_result in event.store_results:
            for var_name, var_value in store_result.items():
                size = self.get_object_size(var_value)
                variable_sizes[var_name] = size
                var_names.append(var_name)
                self._request_counts.total_variable_size += size
        
        # Create metrics
        metrics = StepMetrics(
            session=step.session,
            store_vars=var_names,
            variable_sizes=variable_sizes,
            step=step.step_index,
            phase=phase.name
        )
        
        self.collector.record_step(metrics)
    
    def on_request_start(self, event: RequestStartEvent) -> None:
        """Handle request start event."""
        context = RequestContext(
            id=event.id,
            method=event.method,
            endpoint=event.endpoint,
            start_time=event.timestamp,
            step_id=event.step_id
        )
        self._active_requests[event.id] = context
    
    def on_request_end(self, event: RequestEndEvent) -> None:
        """Handle request end event."""
        request = self._active_requests.pop(event.id)
        step = self._active_steps[request.step_id]
        phase = self._active_phases[step.phase_id]
        
        # Create metrics
        metrics = RequestMetrics(
            method=request.method,
            endpoint=request.endpoint,
            start_time=request.start_time,
            end_time=event.timestamp,
            status_code=event.status_code,
            duration_ms=(event.timestamp - request.start_time).total_seconds() * 1000,
            success=event.success,
            error=event.error,
            errors=event.errors or [],
            request_size_bytes=event.request_size_bytes,
            response_size_bytes=event.response_size_bytes,
            step=step.step_index,
            phase=phase.name
        )
        
        # Update request counts
        if event.request_size_bytes is not None:
            self._request_counts.total_request_size += event.request_size_bytes
        if event.response_size_bytes is not None:
            self._request_counts.total_response_size += event.response_size_bytes
        
        # Increment request counts
        self._request_counts.total += 1
        if event.success:
            self._request_counts.successful += 1
        else:
            self._request_counts.failed += 1
        
        self.collector.record_request(metrics)
    
    def cleanup(self) -> None:
        """Clean up any resources."""
        self._active_requests.clear()
        self._active_steps.clear()
        self._active_phases.clear()
        self._active_playbook = None 