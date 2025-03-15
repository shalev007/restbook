from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

from src.modules.playbook.config import IncrementalConfig

@dataclass
class CheckpointData:
    """Data structure for checkpoint information."""
    current_phase: int
    current_step: int
    variables: Dict[str, Any]
    content_hash: str   # Hash of playbook content to detect changes

class CheckpointStore(ABC):
    """Base class for checkpoint storage implementations."""
    
    @abstractmethod
    def __init__(self, config: IncrementalConfig) -> None:
        """Initialize the checkpoint store."""
        self.config = config

    @abstractmethod
    async def save(self, data: CheckpointData) -> None:
        """Save checkpoint data."""
        pass
    
    @abstractmethod
    async def load(self, content_hash: str) -> Optional[CheckpointData]:
        """Load checkpoint data."""
        pass
    
    @abstractmethod
    async def clear(self, content_hash: str) -> None:
        """Clear checkpoint data."""
        pass 