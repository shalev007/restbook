from typing import Dict
from .base import Authenticator


class BearerAuthenticator(Authenticator):
    """Bearer token authentication."""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        if 'token' not in credentials:
            raise ValueError("Bearer authentication requires 'token' in credentials")
        self.token = credentials['token']
        # Bearer tokens are always authenticated once token is set
        self.is_authenticated = True

    async def authenticate(self) -> None:
        # Bearer tokens are pre-authenticated
        pass

    async def refresh(self) -> None:
        # Bearer tokens don't support refresh
        pass

    def get_headers(self) -> Dict[str, str]:
        super().get_headers()  # Check authentication state
        return {'Authorization': f'Bearer {self.token}'} 