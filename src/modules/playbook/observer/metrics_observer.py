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
class ResourceUsageTracker:
    """Tracks resource usage metrics."""
    peak_memory: int = 0
    cpu_measurements: List[float] = field(default_factory=list)
    
    def update_memory(self, current: Optional[int]) -> None:
        """Update peak memory usage."""
        if current is not None:
            self.peak_memory = max(self.peak_memory, current)
            
    def add_cpu_measurement(self, cpu: Optional[float]) -> None:
        """Add a CPU measurement."""
        if cpu is not None:
            self.cpu_measurements.append(cpu)
            
    def get_average_cpu(self) -> Optional[float]:
        """Calculate average CPU usage."""
        return (sum(self.cpu_measurements) / len(self.cpu_measurements)
                if self.cpu_measurements else None)

@dataclass
class PlaybookContext:
    """Tracks playbook-level context."""
    start_time: datetime
    initial_memory: int = 0

@dataclass
class PhaseContext:
    """Tracks phase-level context."""
    id: str
    name: str
    start_time: datetime
    step_ids: Set[str] = field(default_factory=set)
    initial_memory: int = 0
    initial_cpu: float = 0

@dataclass
class StepContext:
    """Tracks step-level context."""
    id: str
    step_index: int
    session: str
    start_time: datetime
    phase_id: str
    request_ids: Set[str] = field(default_factory=set)
    initial_memory: int = 0
    initial_cpu: float = 0

@dataclass
class RequestContext:
    """Tracks request-level context."""
    id: str
    method: str
    endpoint: str
    start_time: datetime
    step_id: str
    initial_memory: int = 0
    initial_cpu: float = 0

    def end(self, 
            end_time: datetime,
            status_code: int,
            success: bool,
            error: Optional[str] = None,
            errors: Optional[List[str]] = None,
            request_size_bytes: Optional[int] = None,
            response_size_bytes: Optional[int] = None,
            memory_after: Optional[int] = None,
            cpu_after: Optional[float] = None) -> RequestMetrics:
        """Create RequestMetrics from this context."""
        duration_ms = (end_time - self.start_time).total_seconds() * 1000
        
        memory_usage = (
            memory_after - self.initial_memory 
            if self.initial_memory is not None and memory_after is not None 
            else None
        )
        
        cpu_usage = (
            max(0, cpu_after - self.initial_cpu) 
            if self.initial_cpu is not None and cpu_after is not None 
            else None
        )
        
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
            memory_usage_bytes=memory_usage,
            cpu_percent=cpu_usage,
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
        
        # Counters and trackers
        self._request_counts = RequestCounters()
        self._resource_usage = ResourceUsageTracker()
    
    def get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        return self.collector.get_memory_usage()
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return self.collector.get_cpu_usage()
    
    def get_object_size(self, obj: Any) -> int:
        """Get size of an object in bytes."""
        return self.collector.get_object_size(obj)
    
    def on_playbook_start(self, event: PlaybookStartEvent, context_id: str) -> None:
        """Handle playbook start event."""
        self._active_playbook = PlaybookContext(
            start_time=event.timestamp,
            initial_memory=self.get_memory_usage()
        )
    
    def on_playbook_end(self, event: PlaybookEndEvent, context_id: str) -> None:
        """Handle playbook end event."""
        if self._active_playbook is None:
            return
            
        # Get final memory usage and calculate peak
        final_memory = self.get_memory_usage()
        if self._active_playbook.initial_memory is not None and final_memory is not None:
            self._resource_usage.peak_memory = max(self._active_playbook.initial_memory, final_memory)
        
        # Calculate average CPU usage
        average_cpu_percent = self._resource_usage.get_average_cpu()
        
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
            peak_memory_usage_bytes=self._resource_usage.peak_memory,
            average_cpu_percent=average_cpu_percent,
            total_request_size_bytes=self._request_counts.total_request_size,
            total_response_size_bytes=self._request_counts.total_response_size,
            total_variable_size_bytes=self._request_counts.total_variable_size
        )
        
        self.collector.record_playbook(playbook_metrics)
        self.collector.finalize()
    
    def on_phase_start(self, event: PhaseStartEvent, context_id: str) -> None:
        """Handle phase start event."""
        context = PhaseContext(
            id=context_id,
            name=event.phase_name,
            start_time=event.timestamp,
            initial_memory=self.get_memory_usage(),
            initial_cpu=self.get_cpu_usage()
        )
        self._active_phases[context_id] = context
    
    def on_phase_end(self, event: PhaseEndEvent, context_id: str) -> None:
        """Handle phase end event."""
        phase = self._active_phases.pop(context_id)
        memory_after = self.get_memory_usage()
        cpu_after = self.get_cpu_usage()
        
        # Calculate memory usage, ensuring it's never negative
        memory_usage = max(0, memory_after - phase.initial_memory)
        
        # Create metrics
        metrics = PhaseMetrics(
            name=phase.name,
            start_time=phase.start_time,
            end_time=event.timestamp,
            duration_ms=(event.timestamp - phase.start_time).total_seconds() * 1000,
            parallel=event.parallel,
            memory_usage_bytes=memory_usage,
            cpu_percent=max(0, cpu_after - phase.initial_cpu)
        )
        
        self.collector.record_phase(metrics)
    
    def on_step_start(self, event: StepStartEvent, context_id: str) -> None:
        """Handle step start event."""
        context = StepContext(
            id=context_id,
            step_index=event.step_index,
            session=event.session,
            start_time=event.timestamp,
            phase_id=event.phase_context_id,
            initial_memory=self.get_memory_usage(),
            initial_cpu=self.get_cpu_usage()
        )
        self._active_steps[context_id] = context
    
    def on_step_end(self, event: StepEndEvent, context_id: str) -> None:
        """Handle step end event."""
        step = self._active_steps.pop(context_id)
        phase = self._active_phases[step.phase_id]
        memory_after = self.get_memory_usage()
        cpu_after = self.get_cpu_usage()
        
        # Calculate variable sizes
        variable_sizes = {}
        for var_name, var_value in event.store_vars.items():
            size = self.get_object_size(var_value)
            variable_sizes[var_name] = size
            self._request_counts.total_variable_size += size
        
        # Create metrics with non-negative memory and CPU values
        metrics = StepMetrics(
            session=step.session,
            retry_count=event.retry_count,
            store_vars=list(event.store_vars.keys()),
            variable_sizes=variable_sizes,
            memory_usage_bytes=max(0, memory_after - step.initial_memory),
            cpu_percent=max(0, cpu_after - step.initial_cpu),
            step=step.step_index,
            phase=phase.name
        )
        
        self.collector.record_step(metrics)
    
    def on_request_start(self, event: RequestStartEvent, context_id: str) -> None:
        """Handle request start event."""
        context = RequestContext(
            id=context_id,
            method=event.method,
            endpoint=event.endpoint,
            start_time=event.timestamp,
            step_id=event.step_id,
            initial_memory=self.get_memory_usage(),
            initial_cpu=self.get_cpu_usage()
        )
        self._active_requests[context_id] = context
    
    def on_request_end(self, event: RequestEndEvent, context_id: str) -> None:
        """Handle request end event."""
        request = self._active_requests.pop(context_id)
        memory_after = self.get_memory_usage()
        cpu_after = self.get_cpu_usage()
        step = self._active_steps[request.step_id]
        phase = self._active_phases[step.phase_id]
        
        # Create metrics with non-negative memory and CPU values
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
            memory_usage_bytes=max(0, memory_after - request.initial_memory),
            cpu_percent=max(0, cpu_after - request.initial_cpu),
            step=step.step_index,
            phase=phase.name
        )
        
        # Update resource usage with non-negative values
        if metrics.memory_usage_bytes is not None:
            self._resource_usage.update_memory(metrics.memory_usage_bytes)
        if metrics.cpu_percent is not None:
            self._resource_usage.add_cpu_measurement(metrics.cpu_percent)
        
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