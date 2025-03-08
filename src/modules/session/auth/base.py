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
        self.is_authenticated = False

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the service.
        
        Raises:
            ValueError: If authentication fails
        """
        pass

    @abstractmethod
    async def refresh(self) -> None:
        """Refresh authentication if needed.
        
        Raises:
            ValueError: If refresh fails
        """
        pass

    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """Get headers for authenticated requests.
        
        Returns:
            Dict[str, str]: Headers to include in requests
            
        Raises:
            ValueError: If not authenticated
        """
        if not self.is_authenticated:
            raise ValueError("Not authenticated")
        return {}