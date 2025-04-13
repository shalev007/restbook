from typing import Optional

from src.modules.session.session_provider import SessionProvider
from src.modules.logging import BaseLogger

from .file import FileCheckpointStore
from .remote import RemoteCheckpointStore
from ..config import IncrementalConfig, IncrementalStoreType
from .base import CheckpointStore

def create_checkpoint_store(
    config: IncrementalConfig,
    session_provider: SessionProvider,
    logger: BaseLogger
) -> Optional[CheckpointStore]:
    """
    Create a checkpoint store based on configuration.
    
    Args:
        config: Incremental execution configuration
        session_store: Session store for retrieving sessions
        logger: Logger instance
        
    Returns:
        CheckpointStore: The created checkpoint store
    """
    if not config.enabled:
        return None
        
    if config.store == IncrementalStoreType.REMOTE:
        return RemoteCheckpointStore(config, session_provider, logger)
    else:
        return FileCheckpointStore(config) 