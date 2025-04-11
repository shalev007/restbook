from typing import Optional
from ..config import IncrementalConfig
from ...session.session_store import SessionStore
from .base import CheckpointStore, CheckpointData
from ...logging import BaseLogger

class RemoteCheckpointStore(CheckpointStore):
    """Remote implementation of checkpoint storage using a session."""
    
    def __init__(self, config: IncrementalConfig, session_store: SessionStore, logger: BaseLogger):
        super().__init__(config)
        self.logger = logger
        
        if not config.session:
            raise ValueError("session is required for remote checkpoint store")
        if not config.endpoint:
            raise ValueError("endpoint is required for remote checkpoint store")
            
        self.session = session_store.get_session(config.session)
        self.endpoint = config.endpoint.rstrip('/')
        
        # Validate connection immediately
        self.validate_connection()
    
    def validate_connection(self) -> None:
        """Validate we can connect to the checkpoint store."""
        try:
            # Try a HEAD request to validate connection
            response = self.session.head(f"{self.endpoint}/health")
            
            if response.status_code != 200:
                raise ValueError(
                    f"Checkpoint store validation failed: {response.status_code}"
                )
                
            self.logger.log_info("Successfully connected to checkpoint store")
            
        except Exception as e:
            raise ValueError(
                f"Failed to connect to checkpoint store: {str(e)}"
            )
    
    async def save(self, data: CheckpointData) -> None:
        """Save checkpoint data to remote store."""
        try:
            response = await self.session.post(
                f"{self.endpoint}/checkpoints/{data.content_hash}",
                json={
                    "current_phase": data.current_phase,
                    "current_step": data.current_step,
                    "variables": data.variables,
                    "content_hash": data.content_hash
                }
            )
            
            if response.status_code not in (200, 201):
                raise ValueError(
                    f"Failed to save checkpoint: {response.status_code}"
                )
                
            self.logger.log_info(f"Checkpoint saved: {data.content_hash}")
            
        except Exception as e:
            self.logger.log_error(f"Failed to save checkpoint: {str(e)}")
            raise
    
    async def load(self, content_hash: str) -> Optional[CheckpointData]:
        """Load checkpoint data from remote store."""
        try:
            response = await self.session.get(
                f"{self.endpoint}/checkpoints/{content_hash}"
            )
            
            if response.status_code == 404:
                return None
                
            if response.status_code != 200:
                raise ValueError(
                    f"Failed to load checkpoint: {response.status_code}"
                )
                
            data = response.json()
            return CheckpointData(
                current_phase=data["current_phase"],
                current_step=data["current_step"],
                variables=data["variables"],
                content_hash=data["content_hash"]
            )
            
        except Exception as e:
            self.logger.log_error(f"Failed to load checkpoint: {str(e)}")
            raise
    
    async def clear(self, content_hash: str) -> None:
        """Clear checkpoint data from remote store."""
        try:
            response = await self.session.delete(
                f"{self.endpoint}/checkpoints/{content_hash}"
            )
            
            if response.status_code not in (200, 204):
                raise ValueError(
                    f"Failed to clear checkpoint: {response.status_code}"
                )
                
            self.logger.log_info(f"Checkpoint cleared: {content_hash}")
            
        except Exception as e:
            self.logger.log_error(f"Failed to clear checkpoint: {str(e)}")
            raise 