from typing import Dict
from .base import Authenticator


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