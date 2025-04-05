"""Metrics management for playbooks."""
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple, Set
import uuid

from ...metrics import (
    MetricsCollector, 
    RequestMetrics, 
    StepMetrics, 
    PhaseMetrics, 
    PlaybookMetrics
)

class MetricsContext:
    """Holds context data for an active metrics collection."""
    
    def __init__(self, 
                 context_type: str, 
                 start_time: datetime,
                 memory_before: Optional[int] = None,
                 cpu_before: Optional[float] = None,
                 **extra_data: Any):
        """
        Initialize a metrics context.
        
        Args:
            context_type: Type of context (phase, step, request)
            start_time: Start time of the operation
            memory_before: Memory usage at start
            cpu_before: CPU usage at start
            extra_data: Any additional data needed for this context
        """
        self.id = str(uuid.uuid4())
        self.type = context_type
        self.start_time = start_time
        self.memory_before = memory_before
        self.cpu_before = cpu_before
        self.extra_data = extra_data

class MetricsManager:
    """Manages metrics collection for playbooks."""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize the metrics manager.
        
        Args:
            metrics_collector: Optional metrics collector instance
        """
        self.collector = metrics_collector
        self.playbook_start_time: Optional[datetime] = None
        self.initial_memory: Optional[int] = None
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.phases_metrics: List[PhaseMetrics] = []
        self.total_request_size_bytes: int = 0
        self.total_response_size_bytes: int = 0
        self.total_variable_size_bytes: int = 0
        self.peak_memory_usage_bytes: int = 0
        self.cpu_percentages: List[float] = []
        
        # Track active contexts by their ID
        self._active_contexts: Dict[str, MetricsContext] = {}
        
        # Track request counts per step
        self._step_request_counts: Dict[str, Dict[str, int]] = {}
        
        # Track step metrics per phase before they're finalized
        self._phase_steps: Dict[str, List[StepMetrics]] = {}
        
        # Track step context IDs per phase
        self._phase_step_contexts: Dict[str, List[str]] = {}
    
    def start_playbook(self) -> None:
        """Start timing and metrics collection for the playbook."""
        self.playbook_start_time = datetime.now()
        if self.collector:
            self.initial_memory = self.collector.get_memory_usage()
    
    def get_memory_usage(self) -> Optional[int]:
        """Get current memory usage in bytes."""
        return self.collector.get_memory_usage() if self.collector else None
    
    def get_cpu_usage(self) -> Optional[float]:
        """Get current CPU usage percentage."""
        return self.collector.get_cpu_usage() if self.collector else None
    
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
        # Increment global counts
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            
        # Increment step-specific counts if we have a step context
        if step_context_id:
            if step_context_id not in self._step_request_counts:
                self._step_request_counts[step_context_id] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0
                }
            
            self._step_request_counts[step_context_id]["total"] += 1
            if success:
                self._step_request_counts[step_context_id]["successful"] += 1
            else:
                self._step_request_counts[step_context_id]["failed"] += 1
    
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
        if step_context_id not in self._step_request_counts:
            return 0, 0, 0
            
        counts = self._step_request_counts[step_context_id]
        return counts["total"], counts["successful"], counts["failed"]
    
    def get_step_metrics(self, step_context_id: str) -> Optional[StepMetrics]:
        """
        Get metrics for a step if the step has been ended.
        
        Args:
            step_context_id: The context ID of the step
            
        Returns:
            StepMetrics: Metrics for the step, or None if not available
        """
        # Check in the phases_metrics list for this step
        for phase in self.phases_metrics:
            for step in phase.steps:
                if hasattr(step, 'context_id') and step.context_id == step_context_id:
                    return step
        
        return None
    
    def get_phase_metrics(self, phase_context_id: str) -> Optional[PhaseMetrics]:
        """
        Get metrics for a phase if the phase has been ended.
        
        Args:
            phase_context_id: The context ID of the phase
            
        Returns:
            PhaseMetrics: Metrics for the phase, or None if not available
        """
        # Check if we have a phase with this context ID
        for phase in self.phases_metrics:
            if hasattr(phase, 'context_id') and phase.context_id == phase_context_id:
                return phase
        
        return None
    
    def get_phase_steps(self, phase_context_id: str) -> List[StepMetrics]:
        """
        Get the step metrics for a specific phase.
        
        Args:
            phase_context_id: The context ID of the phase
            
        Returns:
            List[StepMetrics]: List of step metrics for the phase
        """
        # First try to get steps from the tracking map for active phases
        if phase_context_id in self._phase_steps:
            return self._phase_steps[phase_context_id]
        
        # If not found, check in completed phases
        phase = self.get_phase_metrics(phase_context_id)
        return phase.steps if phase else []
    
    def get_all_step_metrics(self) -> List[StepMetrics]:
        """
        Get all step metrics from all phases.
        
        Returns:
            List[StepMetrics]: List of all step metrics
        """
        steps = []
        for phase in self.phases_metrics:
            steps.extend(phase.steps)
        return steps
    
    def start_phase(self, name: str) -> str:
        """
        Start timing and metrics collection for a phase.
        
        Args:
            name: The name of the phase
            
        Returns:
            str: Context ID for the phase
        """
        start_time = datetime.now()
        memory_before = self.get_memory_usage()
        cpu_before = self.get_cpu_usage()
        
        context = MetricsContext(
            context_type="phase",
            start_time=start_time,
            memory_before=memory_before,
            cpu_before=cpu_before,
            name=name
        )
        
        self._active_contexts[context.id] = context
        
        # Initialize lists to track step contexts and metrics for this phase
        self._phase_step_contexts[context.id] = []
        self._phase_steps[context.id] = []
        
        return context.id
    
    def end_phase(
        self, 
        context_id: str,
        steps_metrics: Optional[List[StepMetrics]] = None,
        parallel: bool = False
    ) -> PhaseMetrics:
        """
        End timing and metrics collection for a phase.
        
        Args:
            context_id: The context ID returned from start_phase
            steps_metrics: Optional list of step metrics (deprecated, metrics are now tracked internally)
            parallel: Whether the phase steps were executed in parallel
            
        Returns:
            PhaseMetrics: Metrics for the phase
            
        Raises:
            ValueError: If the context ID is not found or not a phase context
        """
        if context_id not in self._active_contexts:
            raise ValueError(f"No active context found with ID: {context_id}")
        
        context = self._active_contexts.pop(context_id)
        if context.type != "phase":
            raise ValueError(f"Context {context_id} is not a phase context")
        
        end_time = datetime.now()
        duration_ms = (end_time - context.start_time).total_seconds() * 1000
        
        memory_after = self.get_memory_usage()
        cpu_after = self.get_cpu_usage()
        
        memory_usage = (
            memory_after - context.memory_before 
            if context.memory_before is not None and memory_after is not None 
            else None
        )
        
        cpu_usage = (
            max(0, cpu_after - context.cpu_before) 
            if context.cpu_before is not None and cpu_after is not None 
            else None
        )
        
        # Use internally tracked step metrics if not provided
        if steps_metrics is None and context_id in self._phase_steps:
            steps_metrics = self._phase_steps[context_id]
        elif steps_metrics is None:
            steps_metrics = []
        
        # Store context ID in extra data for reference
        extra_data = {
            "context_id": context_id
        }
        
        phase_metrics = PhaseMetrics(
            name=context.extra_data["name"],
            start_time=context.start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            steps=steps_metrics,
            parallel=parallel,
            memory_usage_bytes=memory_usage,
            cpu_percent=cpu_usage
        )
        
        # Attach extra data as attributes to the metrics object for future reference
        for key, value in extra_data.items():
            setattr(phase_metrics, key, value)
        
        self.phases_metrics.append(phase_metrics)
        
        if self.collector:
            self.collector.record_phase(phase_metrics)
        
        # Clean up step tracking for this phase
        if context_id in self._phase_steps:
            del self._phase_steps[context_id]
        if context_id in self._phase_step_contexts:
            del self._phase_step_contexts[context_id]
            
        return phase_metrics
    
    def start_step(self, session: str, phase_context_id: Optional[str] = None) -> str:
        """
        Start timing and metrics collection for a step.
        
        Args:
            session: The session name for this step
            phase_context_id: Optional ID of the parent phase context
            
        Returns:
            str: Context ID for the step
        """
        start_time = datetime.now()
        memory_before = self.get_memory_usage()
        cpu_before = self.get_cpu_usage()
        
        context = MetricsContext(
            context_type="step",
            start_time=start_time,
            memory_before=memory_before,
            cpu_before=cpu_before,
            session=session,
            request_context_ids=[],  # Track request contexts that belong to this step
            phase_context_id=phase_context_id  # Link to parent phase
        )
        
        self._active_contexts[context.id] = context
        
        # Initialize request counts for this step
        self._step_request_counts[context.id] = {
            "total": 0,
            "successful": 0,
            "failed": 0
        }
        
        # Add step context to phase if provided
        if phase_context_id and phase_context_id in self._phase_step_contexts:
            self._phase_step_contexts[phase_context_id].append(context.id)
        
        return context.id
    
    def end_step(
        self,
        context_id: str,
        request_metrics: Optional[RequestMetrics] = None,  # Now optional, can be determined internally
        retry_count: int = 0,
        store_vars: List[str] = [],
        variable_sizes: Dict[str, int] = {}
    ) -> StepMetrics:
        """
        End timing and metrics collection for a step.
        
        Args:
            context_id: The context ID returned from start_step
            request_metrics: Optional metrics for the step's request (deprecated, provided for backward compatibility)
            retry_count: Number of retry attempts
            store_vars: Variables stored by the step
            variable_sizes: Sizes of variables stored by the step
            
        Returns:
            StepMetrics: Metrics for the step
            
        Raises:
            ValueError: If the context ID is not found or not a step context
        """
        if context_id not in self._active_contexts:
            raise ValueError(f"No active context found with ID: {context_id}")
        
        context = self._active_contexts.pop(context_id)
        if context.type != "step":
            raise ValueError(f"Context {context_id} is not a step context")
        
        end_time = datetime.now()
        duration_ms = (end_time - context.start_time).total_seconds() * 1000
        
        memory_after = self.get_memory_usage()
        cpu_after = self.get_cpu_usage()
        
        memory_usage = (
            memory_after - context.memory_before 
            if context.memory_before is not None and memory_after is not None 
            else None
        )
        
        cpu_usage = (
            max(0, cpu_after - context.cpu_before) 
            if context.cpu_before is not None and cpu_after is not None 
            else None
        )
        
        # If no explicit request_metrics provided, check if this step has any associated requests
        if not request_metrics and 'request_context_ids' in context.extra_data and context.extra_data['request_context_ids']:
            # Use the first request as the primary one for this step
            # In the future, this could be expanded to handle multiple requests per step
            request_id = context.extra_data['request_context_ids'][0]
            if request_id in self._active_contexts:
                # Request context still active, end it
                request_metrics = self.end_request(
                    context_id=request_id,
                    status_code=0,
                    success=False,
                    error="Request not properly ended"
                )
        
        if not request_metrics:
            # Create a default RequestMetrics if none provided
            request_metrics = RequestMetrics(
                method="NONE",
                endpoint="",
                start_time=context.start_time,
                end_time=end_time,
                status_code=0,
                duration_ms=duration_ms,
                success=False,
                error="No requests executed"
            )
        
        # Get the request counts for this step
        total_count, successful_count, failed_count = 0, 0, 0
        if context_id in self._step_request_counts:
            counts = self._step_request_counts[context_id]
            total_count = counts["total"]
            successful_count = counts["successful"]
            failed_count = counts["failed"]
        
        # Store context ID and request counts in extra data for reference
        # but don't pass them to StepMetrics constructor since it doesn't accept them
        extra_data = {
            "context_id": context_id,
            "total_requests": total_count,
            "successful_requests": successful_count,
            "failed_requests": failed_count,
            "phase_context_id": context.extra_data.get("phase_context_id")
        }
        
        step_metrics = StepMetrics(
            session=context.extra_data["session"],
            request=request_metrics,
            retry_count=retry_count,
            store_vars=store_vars,
            variable_sizes=variable_sizes,
            memory_usage_bytes=memory_usage,
            cpu_percent=cpu_usage
        )
        
        # Attach extra data as attributes to the metrics object for future reference
        for key, value in extra_data.items():
            setattr(step_metrics, key, value)
        
        # Add step metrics to phase if linked
        phase_context_id = context.extra_data.get("phase_context_id")
        if phase_context_id and phase_context_id in self._phase_steps:
            self._phase_steps[phase_context_id].append(step_metrics)
        
        if self.collector:
            self.collector.record_step(step_metrics)
            
        # Clean up request counts for this step
        if context_id in self._step_request_counts:
            del self._step_request_counts[context_id]
            
        return step_metrics
    
    def start_request(self, method: str, endpoint: str, step_context_id: Optional[str] = None) -> str:
        """
        Start timing and metrics collection for a request.
        
        Args:
            method: HTTP method
            endpoint: Request endpoint
            step_context_id: Optional ID of the parent step context
            
        Returns:
            str: Context ID for the request
        """
        start_time = datetime.now()
        memory_before = self.get_memory_usage()
        cpu_before = self.get_cpu_usage()
        
        context = MetricsContext(
            context_type="request",
            start_time=start_time,
            memory_before=memory_before,
            cpu_before=cpu_before,
            method=method,
            endpoint=endpoint,
            step_context_id=step_context_id  # Link to parent step
        )
        
        # Add request context ID to the parent step if provided
        if step_context_id and step_context_id in self._active_contexts:
            step_context = self._active_contexts[step_context_id]
            if 'request_context_ids' in step_context.extra_data:
                step_context.extra_data['request_context_ids'].append(context.id)
        
        self._active_contexts[context.id] = context
        return context.id
    
    def end_request(
        self,
        context_id: str,
        status_code: int,
        success: bool,
        error: Optional[str] = None,
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
            ValueError: If the context ID is not found or not a request context
        """
        if context_id not in self._active_contexts:
            raise ValueError(f"No active context found with ID: {context_id}")
        
        context = self._active_contexts.pop(context_id)
        if context.type != "request":
            raise ValueError(f"Context {context_id} is not a request context")
        
        end_time = datetime.now()
        duration_ms = (end_time - context.start_time).total_seconds() * 1000
        
        memory_after = self.get_memory_usage()
        cpu_after = self.get_cpu_usage()
        
        memory_usage = (
            memory_after - context.memory_before 
            if context.memory_before is not None and memory_after is not None 
            else None
        )
        
        cpu_usage = (
            max(0, cpu_after - context.cpu_before) 
            if context.cpu_before is not None and cpu_after is not None 
            else None
        )
        
        if cpu_usage is not None:
            self.cpu_percentages.append(cpu_usage)
        
        # Update request and response size totals
        if request_size_bytes is not None:
            self.total_request_size_bytes += request_size_bytes
        if response_size_bytes is not None:
            self.total_response_size_bytes += response_size_bytes
        
        # Increment request counts for both global and step contexts
        step_context_id = context.extra_data.get("step_context_id")
        self.increment_request_count(step_context_id, success)
        
        request_metrics = RequestMetrics(
            method=context.extra_data["method"],
            endpoint=context.extra_data["endpoint"],
            start_time=context.start_time,
            end_time=end_time,
            status_code=status_code,
            duration_ms=duration_ms,
            success=success,
            error=error,
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
            memory_usage_bytes=memory_usage,
            cpu_percent=cpu_usage
        )
        
        if self.collector:
            self.collector.record_request(request_metrics)
            
        return request_metrics
    
    def update_variable_size(self, var_name: str, var_value: Any) -> None:
        """Update the total variable size with a new variable."""
        if not self.collector:
            return
            
        size = self.collector.get_object_size(var_value)
        self.total_variable_size_bytes += size
    
    def finalize_playbook(self) -> None:
        """Finalize playbook metrics collection."""
        if not self.collector or self.playbook_start_time is None:
            return
            
        # Get final memory usage and calculate peak
        final_memory = self.get_memory_usage()
        if self.initial_memory is not None and final_memory is not None:
            self.peak_memory_usage_bytes = max(self.initial_memory, final_memory)
        
        # Calculate average CPU usage
        average_cpu_percent = (
            sum(self.cpu_percentages) / len(self.cpu_percentages) 
            if self.cpu_percentages 
            else None
        )
        
        # Record playbook metrics
        playbook_end_time = datetime.now()
        playbook_duration_ms = (playbook_end_time - self.playbook_start_time).total_seconds() * 1000
        
        playbook_metrics = PlaybookMetrics(
            start_time=self.playbook_start_time,
            end_time=playbook_end_time,
            duration_ms=playbook_duration_ms,
            phases=self.phases_metrics,
            total_requests=self.total_requests,
            successful_requests=self.successful_requests,
            failed_requests=self.failed_requests,
            total_duration_ms=playbook_duration_ms,
            peak_memory_usage_bytes=self.peak_memory_usage_bytes,
            average_cpu_percent=average_cpu_percent,
            total_request_size_bytes=self.total_request_size_bytes,
            total_response_size_bytes=self.total_response_size_bytes,
            total_variable_size_bytes=self.total_variable_size_bytes
        )
        
        self.collector.record_playbook(playbook_metrics)
        self.collector.finalize()
        
    def cleanup(self) -> None:
        """Clean up any active contexts (e.g., in case of errors)."""
        self._active_contexts.clear() 
        self._step_request_counts.clear() 