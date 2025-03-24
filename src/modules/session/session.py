import os
import uuid
from dataclasses import dataclass
from typing import Dict, Any, Optional
from .auth import AuthConfig, create_authenticator, Authenticator
from .swagger import SwaggerClient, SwaggerClientFactory


@dataclass
class Session:
    """Represents an API session with authentication."""
    name: str
    base_url: str
    auth_config: Optional[AuthConfig] = None
    swagger_spec_path: Optional[str] = None
    
    def __post_init__(self):
        """Initialize the authenticator if auth config is provided."""
        self.authenticator: Optional[Authenticator] = None
        self._swagger_client: Optional[SwaggerClient] = None
        
        if self.auth_config:
            self.authenticator = create_authenticator(self.auth_config)

    async def authenticate(self) -> None:
        """Authenticate the session if needed."""
        if not self.authenticator:
            return
        try:
            await self.authenticator.authenticate()
        except Exception as e:
            self.authenticator.is_authenticated = False
            raise ValueError(f"Authentication failed: {str(e)}")

    async def refresh_auth(self) -> None:
        """Refresh authentication if possible."""
        if not self.authenticator:
            return
        try:
            await self.authenticator.refresh()
        except Exception as e:
            self.authenticator.is_authenticated = False
            raise ValueError(f"Authentication refresh failed: {str(e)}")

    def get_headers(self) -> Dict[str, str]:
        """Get headers for the request, including authentication if configured."""
        if not self.authenticator:
            return {}
        try:
            return self.authenticator.get_headers()
        except ValueError as e:
            # Re-raise with more context
            raise ValueError(f"Failed to get authentication headers: {str(e)}")

    def is_authenticated(self) -> bool:
        """Check if the session is authenticated."""
        return self.authenticator.is_authenticated if self.authenticator else True

    def has_swagger(self) -> bool:
        """Check if the session has a Swagger specification."""
        return bool(self.swagger_spec_path) and os.path.exists(self.swagger_spec_path or "")

    def get_swagger_source(self) -> Optional[str]:
        """Get the path to the Swagger specification."""
        return self.swagger_spec_path
    
    @property
    def swagger_client(self) -> Optional[SwaggerClient]:
        """
        Get the Swagger client for this session.
        
        Returns:
            SwaggerClient: Swagger client instance or None if not available
        """
        if not self.has_swagger() or not self.swagger_spec_path:
            return None
            
        # Lazy initialization
        if self._swagger_client is None:
            self._swagger_client = SwaggerClientFactory.create_from_file(self.swagger_spec_path)
            
        return self._swagger_client

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
            auth_config=auth_config,
            swagger_spec_path=data.get('swagger_spec_path')
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
        if self.swagger_spec_path:
            data['swagger_spec_path'] = self.swagger_spec_path
        return data
