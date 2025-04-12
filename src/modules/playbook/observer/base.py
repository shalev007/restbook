"""Base observer interface for execution events."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from .events import (
    PlaybookStartEvent, PlaybookEndEvent,
    PhaseStartEvent, PhaseEndEvent,
    StepStartEvent, StepEndEvent,
    RequestStartEvent, RequestEndEvent
)

class ExecutionObserver(ABC):
    """Base class for execution observers."""
    
    @abstractmethod
    def on_playbook_start(self, event: PlaybookStartEvent) -> None:
        """Handle playbook start event.
        
        Args:
            event: The playbook start event
            context_id: The context ID for this playbook execution
        """
        pass
    
    @abstractmethod
    def on_playbook_end(self, event: PlaybookEndEvent) -> None:
        """Handle playbook end event.
        
        Args:
            event: The playbook end event
            context_id: The context ID for this playbook execution
        """
        pass
    
    @abstractmethod
    def on_phase_start(self, event: PhaseStartEvent) -> None:
        """Handle phase start event.
        
        Args:
            event: The phase start event
            context_id: The context ID for this phase
        """
        pass
    
    @abstractmethod
    def on_phase_end(self, event: PhaseEndEvent) -> None:
        """Handle phase end event.
        
        Args:
            event: The phase end event
            context_id: The context ID for this phase
        """
        pass
    
    @abstractmethod
    def on_step_start(self, event: StepStartEvent) -> None:
        """Handle step start event.
        
        Args:
            event: The step start event
            context_id: The context ID for this step
        """
        pass
    
    @abstractmethod
    def on_step_end(self, event: StepEndEvent) -> None:
        """Handle step end event.
        
        Args:
            event: The step end event
            context_id: The context ID for this step
        """
        pass
    
    @abstractmethod
    def on_request_start(self, event: RequestStartEvent) -> None:
        """Handle request start event.
        
        Args:
            event: The request start event
            context_id: The context ID for this request
        """
        pass
    
    @abstractmethod
    def on_request_end(self, event: RequestEndEvent) -> None:
        """Handle request end event.
        
        Args:
            event: The request end event
            context_id: The context ID for this request
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up any resources used by the observer."""
        pass 