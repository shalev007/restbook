"""Observer management for playbook execution."""
from typing import List, Any
from src.modules.logging import BaseLogger
from src.modules.playbook.metrics import create_metrics_collector
from src.modules.playbook.observer import (
    ExecutionObserver,
    PlaybookStartEvent, PlaybookEndEvent,
    PhaseStartEvent, PhaseEndEvent,
    StepStartEvent, StepEndEvent,
    RequestStartEvent, RequestEndEvent
)
from src.modules.playbook.observer.metrics_observer import MetricsObserver
from src.modules.playbook.config import PlaybookConfig

class ObserverManager:
    """Manages observers for playbook execution."""
    
    def __init__(self, config: PlaybookConfig, logger: BaseLogger):
        """Initialize observer manager.
        
        Args:
            config: Playbook configuration
            logger: Logger instance
        """
        self.observers: List[ExecutionObserver] = []
        self.logger = logger
        
        # Initialize metrics observer if enabled
        if config.metrics and config.metrics.enabled:
            metrics_collector = create_metrics_collector(config.metrics)
            self.observers.append(MetricsObserver(metrics_collector))
            logger.log_info(f"Metrics collection enabled with collector type: {config.metrics.collector}")

    def notify(self, event: Any) -> None:
        """Notify all observers of an event."""
        for observer in self.observers:
            if isinstance(event, PlaybookStartEvent):
                observer.on_playbook_start(event)
            elif isinstance(event, PlaybookEndEvent):
                observer.on_playbook_end(event)
            elif isinstance(event, PhaseStartEvent):
                observer.on_phase_start(event)
            elif isinstance(event, PhaseEndEvent):
                observer.on_phase_end(event)
            elif isinstance(event, StepStartEvent):
                observer.on_step_start(event)
            elif isinstance(event, StepEndEvent):
                observer.on_step_end(event)
            elif isinstance(event, RequestStartEvent):
                observer.on_request_start(event)
            elif isinstance(event, RequestEndEvent):
                observer.on_request_end(event)

    def cleanup(self) -> None:
        """Clean up all observers."""
        for observer in self.observers:
            observer.cleanup() 