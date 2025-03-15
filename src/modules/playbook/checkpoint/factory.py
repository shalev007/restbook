from typing import Dict, Type

from ..config import IncrementalConfig, IncrementalStoreType
from .base import CheckpointStore
from .file import FileCheckpointStore

def create_checkpoint_store(config: IncrementalConfig) -> CheckpointStore:
    """Create a checkpoint store based on the configuration."""
    store_types: Dict[IncrementalStoreType, Type[CheckpointStore]] = {
        IncrementalStoreType.FILE: FileCheckpointStore,
    }
    
    if config.store not in store_types:
        raise ValueError(f"Unsupported checkpoint store type: {config.store}")
    
    store_class = store_types[config.store]
    
    if config.store == IncrementalStoreType.FILE:
        if not config.file_path:
            raise ValueError("file_path is required for file-based checkpoint store")
        return store_class(config)
    
    # Add other store type initializations here as they are added
    
    raise ValueError(f"Unsupported checkpoint store type: {config.store}") 