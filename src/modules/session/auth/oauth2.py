from typing import Dict, Optional
import aiohttp
from .base import Authenticator


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