from typing import Optional, Dict, Any
import hashlib
import json

from ..checkpoint import CheckpointStore, CheckpointData, create_checkpoint_store
from ..config import PlaybookConfig
from ...logging import BaseLogger

class CheckpointManager:
    """Manages checkpoint functionality for playbook execution."""
    
    def __init__(self, config: PlaybookConfig, logger: BaseLogger):
        """
        Initialize the checkpoint manager.
        
        Args:
            config: The playbook configuration
            logger: Logger instance for logging
        """
        self.config = config
        self.logger = logger
        self.content_hash: Optional[str] = None
        self.checkpoint_store: Optional[CheckpointStore] = None
        self.enabled = (self.config.incremental and self.config.incremental.enabled) or False

        if self.enabled:
            self.content_hash = self._generate_content_hash()
            self.checkpoint_store = create_checkpoint_store(self.config.incremental) # type: ignore
            self.logger.log_info(f"Incremental execution enabled. Content hash: {self.content_hash}")

    def is_enabled(self) -> bool:
        """
        Check if incremental execution is enabled.
        
        Returns:
            bool: True if incremental execution is enabled, False otherwise
        """
        return self.enabled

    def _generate_content_hash(self) -> str:
        """
        Generate a hash of the playbook content.
        
        Returns:
            str: The MD5 hash of the playbook content
        """
        # Convert config to JSON string
        config_str = json.dumps(self.config.model_dump(exclude={"incremental"}), sort_keys=True)
        # Generate hash
        return hashlib.md5(config_str.encode()).hexdigest()

    async def save_checkpoint(self, phase_index: int, step_index: int, variables: Dict[str, Any]) -> None:
        """
        Save execution checkpoint.
        
        Args:
            phase_index: Current phase index
            step_index: Current step index
            variables: Current variables state
        """
        if not self.checkpoint_store or not self.content_hash:
            return
            
        # Don't save checkpoint if we're at the very first step
        if phase_index == 0 and step_index == 0:
            self.logger.log_info("Skipping checkpoint save for first step")
            return
            
        try:
            checkpoint = CheckpointData(
                current_phase=phase_index,
                current_step=step_index,
                variables=variables,
                content_hash=self.content_hash
            )
            
            await self.checkpoint_store.save(checkpoint)
            self.logger.log_info(f"Checkpoint saved: Phase {phase_index}, Step {step_index}")
        except Exception as e:
            self.logger.log_error(f"Failed to save checkpoint: {str(e)}")

    async def load_checkpoint(self) -> Optional[CheckpointData]:
        """
        Load execution checkpoint.
        
        Returns:
            Optional[CheckpointData]: The loaded checkpoint data if available
        """
        if not self.checkpoint_store or not self.content_hash:
            return None
            
        try:
            checkpoint = await self.checkpoint_store.load(self.content_hash)
            if checkpoint:
                self.logger.log_info(f"Checkpoint loaded: Phase {checkpoint.current_phase}, Step {checkpoint.current_step}")
            return checkpoint
        except Exception as e:
            self.logger.log_error(f"Failed to load checkpoint: {str(e)}")
            return None

    async def clear_checkpoint(self) -> None:
        """Clear execution checkpoint."""
        if not self.checkpoint_store or not self.content_hash:
            return
            
        try:
            await self.checkpoint_store.clear(self.content_hash)
            self.logger.log_info("Checkpoint cleared")
        except Exception as e:
            self.logger.log_error(f"Failed to clear checkpoint: {str(e)}")

    def should_skip_phase(self, phase_index: int, checkpoint: Optional[CheckpointData]) -> bool:
        """
        Determine if a phase should be skipped based on checkpoint.
        
        Args:
            phase_index: The phase index to check
            checkpoint: The current checkpoint data
            
        Returns:
            bool: True if the phase should be skipped
        """
        return bool(checkpoint and phase_index < checkpoint.current_phase)

    def should_skip_step(self, phase_index: int, step_index: int, checkpoint: Optional[CheckpointData]) -> bool:
        """
        Determine if a step should be skipped based on checkpoint.
        
        Args:
            phase_index: The phase index
            step_index: The step index to check
            checkpoint: The current checkpoint data
            
        Returns:
            bool: True if the step should be skipped
        """
        return bool(
            checkpoint and 
            phase_index == checkpoint.current_phase and 
            step_index <= checkpoint.current_step
        )

    def should_restart_parallel_phase(self, phase_index: int, checkpoint: Optional[CheckpointData]) -> bool:
        """
        Determine if a parallel phase should be restarted based on checkpoint.
        
        Args:
            phase_index: The phase index
            checkpoint: The current checkpoint data
            
        Returns:
            bool: True if the phase should be restarted
        """
        return bool(checkpoint and phase_index == checkpoint.current_phase) 