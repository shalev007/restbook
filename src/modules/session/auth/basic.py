import base64
from typing import Dict
from .base import Authenticator


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