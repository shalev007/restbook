from datetime import datetime
from pathlib import Path
import json
import os
from typing import Optional

from src.modules.playbook.config import IncrementalConfig
from .base import CheckpointStore, CheckpointData

class FileCheckpointStore(CheckpointStore):
    """File-based implementation of checkpoint storage."""
    
    def __init__(self, config: IncrementalConfig):
        super().__init__(config)
        if not self.config.file_path:
            raise ValueError("file_path is required for file-based checkpoint store")

        self.base_path = Path(os.path.expanduser(self.config.file_path))
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_checkpoint_path(self, content_hash: str) -> Path:
        """Get the path to the checkpoint file."""
        return self.base_path / f"{content_hash}.json"
    
    async def save(self, data: CheckpointData) -> None:
        """Save checkpoint data to a file."""
        checkpoint_path = self._get_checkpoint_path(data.content_hash)
        
        # Add timestamp when saving
        checkpoint_data = {
            "current_phase": data.current_phase,
            "current_step": data.current_step,
            "variables": data.variables,
            "content_hash": data.content_hash,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint_data, f, indent=2)
    
    async def load(self, content_hash: str) -> Optional[CheckpointData]:
        """Load checkpoint data from a file."""
        checkpoint_path = self._get_checkpoint_path(content_hash)
        
        if not checkpoint_path.exists():
            return None
        
        try:
            with open(checkpoint_path, "r") as f:
                data = json.load(f)
            
            # Validate content hash before returning
            if data["content_hash"] != content_hash:
                return None
                
            return CheckpointData(
                current_phase=data["current_phase"],
                current_step=data["current_step"],
                variables=data["variables"],
                content_hash=data["content_hash"]
            )
        except Exception:
            return None
    
    async def clear(self, content_hash: str) -> None:
        """Clear checkpoint data for a playbook."""
        checkpoint_path = self._get_checkpoint_path(content_hash)
        if checkpoint_path.exists():
            checkpoint_path.unlink() 