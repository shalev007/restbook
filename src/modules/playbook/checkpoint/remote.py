from typing import Optional
from ..config import IncrementalConfig
from ...session.session_store import SessionStore
from .base import CheckpointStore, CheckpointData
from ...logging import BaseLogger
from ...request.resilient_http_client import ResilientHttpClient, ResilientHttpClientConfig, HttpRequestSpec

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
        
        # Initialize the resilient HTTP client
        client_config = ResilientHttpClientConfig(
            timeout=30,  # 30 second timeout
            verify_ssl=True,
            max_retries=3,  # Retry up to 3 times
            backoff_factor=1.0,  # Exponential backoff
            max_delay=60  # Maximum 60 second delay between retries
        )
        self.http_client = ResilientHttpClient(
            session=self.session,
            config=client_config,
            logger=logger
        )
    
    async def initialize(self) -> None:
        """Initialize the checkpoint store by validating the connection."""
        await self.validate_connection()
    
    async def validate_connection(self) -> None:
        """Validate we can connect to the checkpoint store."""
        try:
            request = HttpRequestSpec(
                url=f"{self.endpoint}/health",
                method="HEAD"
            )
            response = await self.http_client.execute_request(request)
            
            if response.status != 200:
                raise ValueError(
                    f"Checkpoint store validation failed: {response.status}"
                )
            
            self.logger.log_info("Successfully connected to checkpoint store")
            
        except Exception as e:
            raise ValueError(
                f"Failed to connect to checkpoint store: {str(e)}"
            )
    
    async def save(self, data: CheckpointData) -> None:
        """Save checkpoint data to remote store."""
        try:
            request = HttpRequestSpec(
                url=f"{self.endpoint}/checkpoints/{data.content_hash}",
                method="POST",
                headers={"Content-Type": "application/json"},
                data={
                    "current_phase": data.current_phase,
                    "current_step": data.current_step,
                    "variables": data.variables,
                    "content_hash": data.content_hash
                }
            )
            response = await self.http_client.execute_request(request)
            
            if response.status not in (200, 201):
                raise ValueError(
                    f"Failed to save checkpoint: {response.status}"
                )
            
            self.logger.log_info(f"Checkpoint saved: {data.content_hash}")
            
        except Exception as e:
            self.logger.log_error(f"Failed to save checkpoint: {str(e)}")
            raise
    
    async def load(self, content_hash: str) -> Optional[CheckpointData]:
        """Load checkpoint data from remote store."""
        try:
            request = HttpRequestSpec(
                url=f"{self.endpoint}/checkpoints/{content_hash}",
                method="GET"
            )
            response = await self.http_client.execute_request(request)
            
            if response.status == 404:
                return None
            
            if response.status != 200:
                raise ValueError(
                    f"Failed to load checkpoint: {response.status}"
                )
            
            data = await response.json()
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
            request = HttpRequestSpec(
                url=f"{self.endpoint}/checkpoints/{content_hash}",
                method="DELETE"
            )
            response = await self.http_client.execute_request(request)
            
            if response.status not in (200, 204):
                raise ValueError(
                    f"Failed to clear checkpoint: {response.status}"
                )
            
            self.logger.log_info(f"Checkpoint cleared: {content_hash}")
            
        except Exception as e:
            self.logger.log_error(f"Failed to clear checkpoint: {str(e)}")
            raise 