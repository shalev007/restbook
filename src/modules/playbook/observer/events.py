"""Base event classes for the observer pattern."""
from abc import ABC
from datetime import datetime
from typing import Optional, Dict, Any, List

class ExecutionEvent(ABC):
    """Base class for all execution events."""
    def __init__(self, timestamp: Optional[datetime] = None):
        self.timestamp = timestamp or datetime.now()

class PlaybookEvent(ExecutionEvent):
    """Base class for playbook-level events."""
    pass

class PhaseEvent(ExecutionEvent):
    """Base class for phase-level events."""
    def __init__(self, phase_name: str, timestamp: Optional[datetime] = None):
        super().__init__(timestamp)
        self.phase_name = phase_name

class StepEvent(ExecutionEvent):
    """Base class for step-level events."""
    def __init__(self, step_index: int, session: str, timestamp: Optional[datetime] = None):
        super().__init__(timestamp)
        self.step_index = step_index
        self.session = session

class RequestEvent(ExecutionEvent):
    """Base class for request-level events."""
    def __init__(self, method: str, endpoint: str, timestamp: Optional[datetime] = None):
        super().__init__(timestamp)
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
    pass

class PhaseEndEvent(PhaseEvent):
    """Event emitted when a phase ends execution."""
    def __init__(self, phase_name: str, parallel: bool, timestamp: Optional[datetime] = None):
        super().__init__(phase_name, timestamp)
        self.parallel = parallel

class StepStartEvent(StepEvent):
    """Event emitted when a step starts execution."""
    def __init__(self, phase_context_id: str, step_index: int, session: str, timestamp: Optional[datetime] = None):
        super().__init__(step_index, session, timestamp)
        self.phase_context_id = phase_context_id

class StepEndEvent(StepEvent):
    """Event emitted when a step ends execution."""
    def __init__(
        self,
        step_index: int,
        session: str,
        retry_count: int,
        store_vars: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ):
        super().__init__(step_index, session, timestamp)
        self.retry_count = retry_count
        self.store_vars = store_vars

class RequestStartEvent(RequestEvent):
    """Event emitted when a request starts execution."""
    def __init__(self, step_id: str, method: str, endpoint: str, request_uuid: str, timestamp: Optional[datetime] = None):
        super().__init__(method, endpoint, timestamp)
        self.step_id = step_id
        self.request_uuid = request_uuid
class RequestEndEvent(RequestEvent):
    """Event emitted when a request ends execution."""
    def __init__(
        self,
        method: str,
        endpoint: str,
        request_uuid: str,
        status_code: int,
        success: bool,
        error: Optional[str],
        errors: Optional[List[str]],
        request_size_bytes: Optional[int],
        response_size_bytes: Optional[int],
        timestamp: Optional[datetime] = None
    ):
        super().__init__(method, endpoint, timestamp)
        self.status_code = status_code
        self.success = success
        self.error = error
        self.errors = errors
        self.request_size_bytes = request_size_bytes
        self.response_size_bytes = response_size_bytes 
        self.request_uuid = request_uuid