"""Metrics management for playbooks."""
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from dataclasses import dataclass, field
import uuid

from ...metrics import (
    MetricsCollector, 
    RequestMetrics, 
    StepMetrics, 
    PhaseMetrics, 
    PlaybookMetrics
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

class MetricsManager:
    """Manages metrics collection for playbooks."""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize the metrics manager.
        
        Args:
            metrics_collector: Optional metrics collector instance
        """
        self.collector = metrics_collector
        
        # Active execution contexts
        self._active_playbook: Optional[PlaybookContext] = None
        self._active_phases: Dict[str, PhaseContext] = {}
        self._active_steps: Dict[str, StepContext] = {}
        self._active_requests: Dict[str, RequestContext] = {}
        
        # Metrics storage with ID tracking
        self._completed_requests: List[RequestMetrics] = []
        self._request_ids: Dict[str, RequestMetrics] = {}  # Track request IDs
        self._completed_steps: Dict[str, StepMetrics] = {}
        self._completed_phases: List[PhaseMetrics] = []
        self._phase_ids: Dict[str, PhaseMetrics] = {}  # Track phase IDs
        
        # Counters and trackers
        self._request_counts = RequestCounters()
        self._resource_usage = ResourceUsageTracker()
    
    def start_playbook(self) -> None:
        """Start timing and metrics collection for the playbook."""
        start_time = datetime.now()
        initial_memory = self.get_memory_usage()
        self._active_playbook = PlaybookContext(
            start_time=start_time,
            initial_memory=initial_memory
        )
    
    def get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        return self.collector.get_memory_usage() if self.collector else 0
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return self.collector.get_cpu_usage() if self.collector else 0
    
    def get_object_size(self, obj: Any) -> int:
        """Get size of an object in bytes."""
        return self.collector.get_object_size(obj) if self.collector else 0
    
    def increment_request_count(self, step_context_id: Optional[str], success: bool = True) -> None:
        """
        Increment request counts for a step.
        
        Args:
            step_context_id: The context ID of the step
            success: Whether the request was successful
        """
        self._request_counts.total += 1
        if success:
            self._request_counts.successful += 1
        else:
            self._request_counts.failed += 1
    
    def _get_request_success(self, request_id: str) -> bool:
        """Check if a request was successful."""
        request = self._request_ids.get(request_id)
        return request.success if request else False
    
    def get_request_counts(self, step_context_id: str) -> tuple[int, int, int]:
        """
        Get request counts for a step.
        
        Args:
            step_context_id: The context ID of the step
            
        Returns:
            Tuple containing:
            - int: Total number of requests
            - int: Number of successful requests
            - int: Number of failed requests
        """
        step = self._active_steps.get(step_context_id)
        if not step:
            return 0, 0, 0
            
        total = len(step.request_ids)
        successful = sum(1 for req_id in step.request_ids 
                        if self._get_request_success(req_id))
        return total, successful, total - successful
    
    def get_step_metrics(self, step_context_id: str) -> Optional[StepMetrics]:
        """
        Get metrics for a step if the step has been ended.
        
        Args:
            step_context_id: The context ID of the step
            
        Returns:
            StepMetrics: Metrics for the step, or None if not available
        """
        return self._completed_steps.get(step_context_id)
    
    def get_phase_metrics(self, phase_context_id: str) -> Optional[PhaseMetrics]:
        """
        Get metrics for a phase if the phase has been ended.
        
        Args:
            phase_context_id: The context ID of the phase
            
        Returns:
            PhaseMetrics: Metrics for the phase, or None if not available
        """
        return self._phase_ids.get(phase_context_id)
    
    def get_phase_steps(self, phase_context_id: str) -> List[StepMetrics]:
        """
        Get the step metrics for a specific phase.
        
        Args:
            phase_context_id: The context ID of the phase
            
        Returns:
            List[StepMetrics]: List of step metrics for the phase
        """
        phase = self._active_phases.get(phase_context_id)
        if not phase:
            return []
            
        return [
            self._completed_steps[step_id]
            for step_id in phase.step_ids
            if step_id in self._completed_steps
        ]
    
    def get_all_step_metrics(self) -> List[StepMetrics]:
        """
        Get all step metrics.
        
        Returns:
            List[StepMetrics]: List of all step metrics
        """
        return list(self._completed_steps.values())
    
    def start_phase(self, name: str) -> str:
        """
        Start timing and metrics collection for a phase.
        
        Args:
            name: The name of the phase
            
        Returns:
            str: Context ID for the phase
        """
        phase_id = str(uuid.uuid4())
        context = PhaseContext(
            id=phase_id,
            name=name,
            start_time=datetime.now(),
            initial_memory=self.get_memory_usage(),
            initial_cpu=self.get_cpu_usage()
        )
        self._active_phases[phase_id] = context
        return phase_id
    
    def start_step(self, step_index: int, session: str, phase_context_id: str) -> str:
        """
        Start timing and metrics collection for a step.
        
        Args:
            step_index: The index of the step in the phase
            session: The session name for this step
            phase_context_id: Optional ID of the parent phase context
            
        Returns:
            str: Context ID for the step
        """
        step_id = str(uuid.uuid4())
        context = StepContext(
            id=step_id,
            step_index=step_index,
            session=session,
            phase_id=phase_context_id,
            start_time=datetime.now(),
            initial_memory=self.get_memory_usage(),
            initial_cpu=self.get_cpu_usage()
        )
        self._active_steps[step_id] = context
        
        if phase_context_id and phase_context_id in self._active_phases:
            self._active_phases[phase_context_id].step_ids.add(step_id)
            
        return step_id
    
    def start_request(self, method: str, endpoint: str, step_context_id: str) -> str:
        """
        Start timing and metrics collection for a request.
        
        Args:
            method: HTTP method
            endpoint: Request endpoint
            step_context_id: Optional ID of the parent step context
            
        Returns:
            str: Context ID for the request
        """
        request_id = str(uuid.uuid4())
        context = RequestContext(
            id=request_id,
            step_id=step_context_id,
            method=method,
            endpoint=endpoint,
            start_time=datetime.now(),
            initial_memory=self.get_memory_usage(),
            initial_cpu=self.get_cpu_usage()
        )
        self._active_requests[request_id] = context
        
        if step_context_id and step_context_id in self._active_steps:
            self._active_steps[step_context_id].request_ids.add(request_id)
            
        return request_id
    
    def end_request(
        self,
        context_id: str,
        status_code: int,
        success: bool,
        error: Optional[str] = None,
        errors: Optional[List[str]] = None,
        request_size_bytes: Optional[int] = None,
        response_size_bytes: Optional[int] = None
    ) -> RequestMetrics:
        """
        End timing and metrics collection for a request.
        
        Args:
            context_id: The context ID returned from start_request
            status_code: HTTP status code
            success: Whether the request was successful
            error: Error message if request failed
            request_size_bytes: Size of request payload
            response_size_bytes: Size of response payload
            
        Returns:
            RequestMetrics: Metrics for the request
            
        Raises:
            ValueError: If the context ID is not found
        """
        if context_id not in self._active_requests:
            raise ValueError(f"No active request found with ID: {context_id}")
        
        context = self._active_requests.pop(context_id)
        end_time = datetime.now()
        memory_after = self.get_memory_usage()
        cpu_after = self.get_cpu_usage()
        
        # Create metrics
        metrics = context.end(
            end_time=end_time,
            status_code=status_code,
            success=success,
            error=error,
            errors=errors,
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
            memory_after=memory_after,
            cpu_after=cpu_after
        )
        step = self._active_steps.get(context.step_id)
        if step:
            metrics.step = step.step_index
            phase = self._active_phases.get(step.phase_id)
            if phase:
                metrics.phase = phase.name
        
        # Update resource usage
        if metrics.memory_usage_bytes is not None:
            self._resource_usage.update_memory(metrics.memory_usage_bytes)
        if metrics.cpu_percent is not None:
            self._resource_usage.add_cpu_measurement(metrics.cpu_percent)
        
        # Update request counts
        if request_size_bytes is not None:
            self._request_counts.total_request_size += request_size_bytes
        if response_size_bytes is not None:
            self._request_counts.total_response_size += response_size_bytes
        
        # Increment request counts
        self.increment_request_count(context.step_id, success)
        
        # Store and return
        self._completed_requests.append(metrics)
        self._request_ids[context_id] = metrics
        if self.collector:
            self.collector.record_request(metrics)
            
        return metrics
    
    def update_variable_size(self, var_name: str, var_value: Any) -> None:
        """Update the total variable size with a new variable."""
        if not self.collector:
            return
            
        size = self.collector.get_object_size(var_value)
        self._request_counts.total_variable_size += size
    
    def finalize_playbook(self) -> None:
        """Finalize playbook metrics collection."""
        if not self.collector or self._active_playbook is None:
            return
            
        # Get final memory usage and calculate peak
        final_memory = self.get_memory_usage()
        if self._active_playbook.initial_memory is not None and final_memory is not None:
            self._resource_usage.peak_memory = max(self._active_playbook.initial_memory, final_memory)
        
        # Calculate average CPU usage
        average_cpu_percent = self._resource_usage.get_average_cpu()
        
        # Record playbook metrics
        playbook_end_time = datetime.now()
        playbook_duration_ms = (playbook_end_time - self._active_playbook.start_time).total_seconds() * 1000
        
        playbook_metrics = PlaybookMetrics(
            start_time=self._active_playbook.start_time,
            end_time=playbook_end_time,
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
        
    def cleanup(self) -> None:
        """Clean up any active contexts (e.g., in case of errors)."""
        self._active_requests.clear() 
        self._active_steps.clear() 
        self._active_phases.clear() 
        self._active_playbook = None
    
    def end_step(
        self,
        context_id: str,
        retry_count: int = 0,
        store_vars: Optional[List[str]] = None,
        variable_sizes: Optional[Dict[str, int]] = None
    ) -> StepMetrics:
        """
        End timing and metrics collection for a step.
        
        Args:
            context_id: The context ID returned from start_step
            retry_count: Number of retries for this step
            store_vars: List of variables stored during this step
            variable_sizes: Sizes of stored variables in bytes
            
        Returns:
            StepMetrics: Metrics for the step
            
        Raises:
            ValueError: If the context ID is not found
        """
        if context_id not in self._active_steps:
            raise ValueError(f"No active step found with ID: {context_id}")
        
        context = self._active_steps.pop(context_id)
        end_time = datetime.now()
        memory_after = self.get_memory_usage()
        cpu_after = self.get_cpu_usage()
        
        # Calculate memory and CPU usage
        memory_usage = (
            memory_after - context.initial_memory 
            if context.initial_memory is not None and memory_after is not None 
            else None
        )
        
        cpu_usage = (
            max(0, cpu_after - context.initial_cpu) 
            if context.initial_cpu is not None and cpu_after is not None 
            else None
        )
        
        # Create metrics
        metrics = StepMetrics(
            session=context.session,
            retry_count=retry_count,
            store_vars=store_vars or [],
            variable_sizes=variable_sizes or {},
            memory_usage_bytes=memory_usage,
            cpu_percent=cpu_usage,
        )

        phase = self._active_phases.get(context.phase_id)
        if phase:
            metrics.phase = phase.name
        
        # Store and return
        self._completed_steps[context_id] = metrics
        if self.collector:
            self.collector.record_step(metrics)
            
        return metrics
    
    def end_phase(
        self,
        context_id: str,
        parallel: bool = False
    ) -> PhaseMetrics:
        """
        End timing and metrics collection for a phase.
        
        Args:
            context_id: The context ID returned from start_phase
            parallel: Whether the phase was executed in parallel
            
        Returns:
            PhaseMetrics: Metrics for the phase
            
        Raises:
            ValueError: If the context ID is not found
        """
        if context_id not in self._active_phases:
            raise ValueError(f"No active phase found with ID: {context_id}")
        
        context = self._active_phases.pop(context_id)
        end_time = datetime.now()
        memory_after = self.get_memory_usage()
        cpu_after = self.get_cpu_usage()
        
        # Calculate memory and CPU usage
        memory_usage = (
            memory_after - context.initial_memory 
            if context.initial_memory is not None and memory_after is not None 
            else None
        )
        
        cpu_usage = (
            max(0, cpu_after - context.initial_cpu) 
            if context.initial_cpu is not None and cpu_after is not None 
            else None
        )
        
        # Calculate total duration
        duration_ms = (end_time - context.start_time).total_seconds() * 1000
        
        # Create metrics
        metrics = PhaseMetrics(
            name=context.name,
            start_time=context.start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            parallel=parallel,
            memory_usage_bytes=memory_usage,
            cpu_percent=cpu_usage
        )
        
        # Store and return
        self._completed_phases.append(metrics)
        self._phase_ids[context_id] = metrics
        if self.collector:
            self.collector.record_phase(metrics)
            
        return metrics 