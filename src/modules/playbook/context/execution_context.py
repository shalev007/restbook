from dataclasses import dataclass, field
import uuid
from typing import List, Dict, Any

from src.modules.session.session import Session

from ..config import PhaseConfig, StepConfig, RequestConfig

@dataclass
class PhaseContext:
    """Context for a single phase execution."""
    index: int
    config: PhaseConfig
    
    def __post_init__(self):
        self.id = str(uuid.uuid4())
        self.name = self.config.name
        self.parallel = self.config.parallel
        self.steps = self.config.steps

@dataclass
class StepContext:
    """Context for a single step execution."""
    phase_id: str
    index: int
    config: StepConfig
    session: Session
    store_results: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        self.id = str(uuid.uuid4())
        self.iterate = self.config.iterate
        self.parallel = self.config.parallel
        self.store = self.config.store
        self.on_error = self.config.on_error
        self.request = self.config.request

@dataclass
class RequestContext:
    """Context for a single HTTP request execution."""
    step_id: str
    config: RequestConfig
    
    def __post_init__(self):
        self.id = str(uuid.uuid4()) 