from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
import base64
import aiohttp


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


class BearerAuthenticator(Authenticator):
    """Bearer token authentication."""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)

        if 'token' not in credentials:
            raise ValueError("Bearer authentication requires 'token' in credentials")
        self.token = credentials['token']

    async def authenticate(self) -> Dict[str, str]:
        return {'Authorization': f'Bearer {self.token}'}

    async def refresh(self) -> Dict[str, str]:
        # Bearer tokens don't support refresh
        return await self.authenticate()


class BasicAuthenticator(Authenticator):
    """Basic authentication."""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)

        if 'username' not in credentials or 'password' not in credentials:
            raise ValueError("Basic authentication requires 'username' and 'password' in credentials")
        self.username = credentials['username']
        self.password = credentials['password']
        self._auth_header = self._create_auth_header()

    def _create_auth_header(self) -> str:
        auth_string = f"{self.username}:{self.password}"
        auth_bytes = auth_string.encode('utf-8')
        encoded = base64.b64encode(auth_bytes).decode('utf-8')
        return f'Basic {encoded}'

    async def authenticate(self) -> Dict[str, str]:
        return {'Authorization': self._auth_header}

    async def refresh(self) -> Dict[str, str]:
        # Basic auth doesn't support refresh
        return await self.authenticate()


class OAuth2Authenticator(Authenticator):
    """OAuth2 authentication."""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)

        required = {'client_id', 'client_secret', 'token_url'}
        missing = required - credentials.keys()
        if missing:
            raise ValueError(f"OAuth2 authentication requires {', '.join(missing)} in credentials")
        
        self.client_id = credentials['client_id']
        self.client_secret = credentials['client_secret']
        self.token_url = credentials['token_url']
        self.scope = credentials.get('scope')
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    async def authenticate(self) -> Dict[str, str]:
        if self.access_token:
            return {'Authorization': f'Bearer {self.access_token}'}

        # Get initial token
        async with aiohttp.ClientSession() as session:
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }
            if self.scope:
                data['scope'] = self.scope

            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    raise ValueError(f"OAuth2 authentication failed: {await response.text()}")
                
                token_data = await response.json()
                self.access_token = token_data['access_token']
                self.refresh_token = token_data.get('refresh_token')
                
                return {'Authorization': f'Bearer {self.access_token}'}

    async def refresh(self) -> Dict[str, str]:
        if not self.refresh_token:
            # No refresh token, get new access token
            return await self.authenticate()

        async with aiohttp.ClientSession() as session:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }

            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    # Refresh failed, try getting new token
                    return await self.authenticate()
                
                token_data = await response.json()
                self.access_token = token_data['access_token']
                self.refresh_token = token_data.get('refresh_token', self.refresh_token)
                
                return {'Authorization': f'Bearer {self.access_token}'}


def create_authenticator(config: AuthConfig) -> Authenticator:
    """Create an authenticator based on the auth type."""
    auth_types: Dict[str, type[Authenticator]] = {
        'bearer': BearerAuthenticator,
        'basic': BasicAuthenticator,
        'oauth2': OAuth2Authenticator,
    }
    
    if config.type not in auth_types:
        raise ValueError(f"Unsupported authentication type: {config.type}")
    
    return auth_types[config.type](config.credentials) 