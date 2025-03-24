from typing import Dict
from .base import Authenticator


class ApiKeyAuthenticator(Authenticator):
    """API key authentication."""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        if 'api_key' not in credentials:
            raise ValueError("API key authentication requires 'api_key' in credentials")
            
        self.api_key = credentials['api_key']
        # Get header name from credentials or use default
        self.header_name = credentials.get('header_name', 'X-API-Key')
        # API keys are always authenticated once key is set
        self.is_authenticated = True

    async def authenticate(self) -> None:
        # API keys are pre-authenticated
        pass

    async def refresh(self) -> None:
        # API keys don't support refresh
        pass

    def get_headers(self) -> Dict[str, str]:
        super().get_headers()  # Check authentication state
        return {self.header_name: self.api_key} 