from dataclasses import dataclass, field
from typing import List
import asyncio

@dataclass
class ExecutionTracker:
    """Tracks execution state of a playbook."""
    running_requests: List[asyncio.Task] = field(default_factory=list)
    cleanup_done: bool = False
    current_phase_index: int = 0
    current_step_index: int = 0
    
    def track_request(self, task: asyncio.Task) -> None:
        """Add a request task to tracking."""
        self.running_requests.append(task)
        
    def untrack_request(self, task: asyncio.Task) -> None:
        """Remove a request task from tracking."""
        if task in self.running_requests:
            self.running_requests.remove(task)
            
    def mark_cleanup_done(self) -> None:
        """Mark cleanup as completed."""
        self.cleanup_done = True
        
    def advance_step(self) -> None:
        """Move to next step."""
        self.current_step_index += 1
        
    def advance_phase(self) -> None:
        """Move to next phase."""
        self.current_phase_index += 1
        self.current_step_index = 0 