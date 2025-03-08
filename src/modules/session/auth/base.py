from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict


@dataclass
class AuthConfig:
    """Configuration for authentication."""
    type: str
    credentials: Dict[str, str]


class Authenticator(ABC):
    """Base class for authentication methods."""

    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials

    @abstractmethod
    async def authenticate(self) -> Dict[str, str]:
        """Authenticate and return headers to use for requests.
        
        Returns:
            Dict[str, str]: Headers to include in requests
            
        Raises:
            ValueError: If authentication fails
        """
        pass

    @abstractmethod
    async def refresh(self) -> Dict[str, str]:
        """Refresh authentication if needed.
        
        Returns:
            Dict[str, str]: Updated headers to use for requests
            
        Raises:
            ValueError: If refresh fails
        """
        pass 