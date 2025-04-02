import os
import uuid
from dataclasses import dataclass
from typing import Dict, Any, Optional
from .auth import AuthConfig, create_authenticator, Authenticator
from .swagger import SwaggerClient, SwaggerClientFactory
from ..request.circuit_breaker import CircuitBreaker

@dataclass
class RetryConfig:
    """Simple retry configuration for sessions."""
    max_retries: int = 2
    backoff_factor: float = 1.0
    max_delay: Optional[int] = None

@dataclass
class Session:
    """Represents an API session with authentication."""
    name: str
    base_url: str
    auth_config: Optional[AuthConfig] = None
    swagger_spec_path: Optional[str] = None
    retry_config: Optional[RetryConfig] = None
    validate_ssl: Optional[bool] = None
    timeout: Optional[int] = None
    circuit_breaker: Optional[CircuitBreaker] = None
    
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
        
        retry_config = None
        if 'retry' in data and data['retry'] is not None:
            retry_data = data['retry']
            retry_config = RetryConfig(
                max_retries=retry_data.get('max_retries', 2),
                backoff_factor=retry_data.get('backoff_factor', 1.0),
                max_delay=retry_data.get('max_delay')
            )
        
        circuit_breaker = None
        if 'circuit_breaker' in data and data['circuit_breaker'] is not None:
            cb_data = data['circuit_breaker']
            circuit_breaker = CircuitBreaker(
                threshold=cb_data.get('threshold', 2),
                reset_timeout=cb_data.get('reset', 10),
                jitter=cb_data.get('jitter', 0.0)
            )
        
        return cls(
            name=name,
            base_url=data['base_url'],
            auth_config=auth_config,
            swagger_spec_path=data.get('swagger_spec_path'),
            retry_config=retry_config,
            validate_ssl=data.get('validate_ssl'),
            timeout=data.get('timeout'),
            circuit_breaker=circuit_breaker
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
            
        if self.retry_config:
            retry_data: Dict[str, Any] = {
                'max_retries': self.retry_config.max_retries,
                'backoff_factor': self.retry_config.backoff_factor
            }
            if self.retry_config.max_delay is not None:
                retry_data['max_delay'] = self.retry_config.max_delay
            data['retry'] = retry_data
            
        if self.circuit_breaker:
            data['circuit_breaker'] = {
                'threshold': self.circuit_breaker.threshold,
                'reset': self.circuit_breaker.reset_timeout,
                'jitter': self.circuit_breaker.jitter
            }
            
        if self.validate_ssl is not None:
            data['validate_ssl'] = self.validate_ssl
            
        if self.timeout is not None:
            data['timeout'] = self.timeout
            
        if self.swagger_spec_path:
            data['swagger_spec_path'] = self.swagger_spec_path
            
        return data
