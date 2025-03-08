import os
import uuid
from dataclasses import dataclass
from typing import Dict, Any, Optional
from .auth import AuthConfig, create_authenticator, Authenticator


@dataclass
class Session:
    """Represents an API session with authentication."""
    name: str
    base_url: str
    auth_config: Optional[AuthConfig] = None
    
    def __post_init__(self):
        """Initialize the authenticator if auth config is provided."""
        self.authenticator: Optional[Authenticator] = None
        if self.auth_config:
            self.authenticator = create_authenticator(self.auth_config)

    async def get_headers(self) -> Dict[str, str]:
        """Get headers for the request, including authentication if configured."""
        if not self.authenticator:
            return {}
        return await self.authenticator.authenticate()

    async def refresh_auth(self) -> Dict[str, str]:
        """Refresh authentication if possible."""
        if not self.authenticator:
            return {}
        return await self.authenticator.refresh()

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'Session':
        """Create a session from a dictionary."""
        auth_config = None
        if 'auth' in data and data['auth'] is not None:
            auth_config = AuthConfig(
                type=data['auth']['type'],
                credentials=data['auth']['credentials']
            )
        
        return cls(
            name=name,
            base_url=data['base_url'],
            auth_config=auth_config
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the session to a dictionary."""
        data: Dict[str, Any] = {
            'base_url': self.base_url,
            'auth': None
        }
        if self.auth_config:
            data['auth'] = {
                'type': self.auth_config.type,
                'credentials': self.auth_config.credentials
            }
        return data
