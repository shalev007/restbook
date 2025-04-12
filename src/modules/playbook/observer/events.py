"""Base event classes for the observer pattern."""
from abc import ABC
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

from src.modules.playbook.context.execution_context import (
    PhaseContext,
    StepContext,
    RequestContext
)
from src.modules.request.resilient_http_client import RequestExecutionMetadata

@dataclass
class RequestMetadata:
    """Metadata for request execution results."""
    status_code: int
    success: bool
    error: Optional[str] = None
    errors: Optional[List[str]] = None
    request_size_bytes: Optional[int] = None
    response_size_bytes: Optional[int] = None

class ExecutionEvent(ABC):
    """Base class for all execution events."""
    def __init__(self):
        self.timestamp = datetime.now()

class PlaybookEvent(ExecutionEvent):
    """Base class for playbook-level events."""
    pass

class PhaseEvent(ExecutionEvent):
    """Base class for phase-level events."""
    def __init__(self, id: str, phase_name: str):
        super().__init__()
        self.id = id
        self.phase_name = phase_name

class StepEvent(ExecutionEvent):
    """Base class for step-level events."""
    def __init__(self, id: str, step_index: int, session: str):
        super().__init__()
        self.id = id
        self.step_index = step_index
        self.session = session

class RequestEvent(ExecutionEvent):
    """Base class for request-level events."""
    def __init__(self, id: str, method: str, endpoint: str):
        super().__init__()
        self.id = id
        self.method = method
        self.endpoint = endpoint

# Concrete Events
class PlaybookStartEvent(PlaybookEvent):
    """Event emitted when a playbook starts execution."""
    pass

class PlaybookEndEvent(PlaybookEvent):
    """Event emitted when a playbook ends execution."""
    pass

class PhaseStartEvent(PhaseEvent):
    """Event emitted when a phase starts execution."""
    def __init__(self, context: PhaseContext):
        super().__init__(context.id, context.name)

class PhaseEndEvent(PhaseEvent):
    """Event emitted when a phase ends execution."""
    def __init__(self, context: PhaseContext):
        super().__init__(context.id, context.name)
        self.parallel = context.parallel

class StepStartEvent(StepEvent):
    """Event emitted when a step starts execution."""
    def __init__(self, context: StepContext):
        super().__init__(context.id, context.index, context.session.name)
        self.phase_id = context.phase_id
        self.index = context.index
        self.session = context.session.name

class StepEndEvent(StepEvent):
    """Event emitted when a step ends execution."""
    def __init__(self, context: StepContext):
        super().__init__(context.id, context.index, context.session.name)
        self.store_results = context.store_results

class RequestStartEvent(RequestEvent):
    """Event emitted when a request starts execution."""
    def __init__(self, context: RequestContext):
        super().__init__(context.id, context.config.method.value, context.config.endpoint)
        self.step_id = context.step_id

class RequestEndEvent(RequestEvent):
    """Event emitted when a request ends execution."""
    def __init__(
        self, 
        context: RequestContext, 
        metadata: RequestExecutionMetadata
    ):
        super().__init__(context.id, context.config.method.value, context.config.endpoint)
        self.status_code = metadata.status_code or 0
        self.success = metadata.success or False
        self.error = metadata.errors[-1] if metadata.errors else None
        self.errors = metadata.errors
        self.request_size_bytes = metadata.request_size_bytes
        self.response_size_bytes = metadata.response_size_bytes
        self.retry_count = metadata.retry_count