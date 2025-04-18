"""Factory for creating ShutdownCoordinator instances."""

from typing import Dict, TypeVar, Generic, Optional

from ..logging import BaseLogger
from .coordinator import ShutdownCoordinator

# Define a bound type variable
T = TypeVar('T')

class ShutdownCoordinatorFactory:
    """Factory for creating and managing ShutdownCoordinator instances."""
    
    _instance = None
    _coordinators: Dict[str, ShutdownCoordinator] = {}
    
    @classmethod
    def get_instance(cls) -> 'ShutdownCoordinatorFactory':
        """Get or create the singleton factory instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def create_coordinator(self, logger: BaseLogger, name: str = "default") -> ShutdownCoordinator:
        """
        Create a new ShutdownCoordinator instance or return an existing one.
        
        Args:
            logger: Logger instance for the coordinator
            name: Optional name for the coordinator instance
            
        Returns:
            A ShutdownCoordinator instance
        """
        if name not in self._coordinators:
            self._coordinators[name] = ShutdownCoordinator(logger)
        
        return self._coordinators[name]
    
    def get_coordinator(self, name: str = "default") -> Optional[ShutdownCoordinator]:
        """
        Get an existing coordinator by name.
        
        Args:
            name: Name of the coordinator to retrieve
            
        Returns:
            The coordinator instance or None if not found
        """
        return self._coordinators.get(name)
