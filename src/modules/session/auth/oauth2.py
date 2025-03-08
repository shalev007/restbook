from typing import Dict, Optional
import aiohttp
import click
from .base import Authenticator


class OAuth2Authenticator(Authenticator):
    """OAuth2 authentication."""
    
    SUPPORTED_GRANT_TYPES = {
        'client_credentials',  # Server-to-server
        'authorization_code',  # Web application flow
        'password',           # Resource owner password flow
        'refresh_token'       # Refresh token flow
    }
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        required = {'client_id', 'client_secret', 'token_url'}
        missing = required - credentials.keys()
        if missing:
            missing_fields = "', '".join(missing)
            raise ValueError(f"OAuth2 authentication requires '{missing_fields}' in credentials")
        
        self.client_id = credentials['client_id']
        self.client_secret = credentials['client_secret']
        self.token_url = credentials['token_url']
        self.scope = credentials.get('scope')
        
        # Custom keys for request parameters
        self.client_id_key = credentials.get('client_id_key', 'client_id')
        self.client_secret_key = credentials.get('client_secret_key', 'client_secret')
        self.access_token_key = credentials.get('access_token_key', 'access_token')
        self.refresh_token_key = credentials.get('refresh_token_key', 'refresh_token')
        self.grant_type = credentials.get('grant_type')
        
        if self.grant_type:
            click.echo(f"Warning: Grant type {self.grant_type} is not yet supported. this is a development feature.")
            self._set_up_grant_type()
            
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def _set_up_grant_type(self):
        match self.grant_type:
            case 'password':
                if 'username' not in self.credentials or 'password' not in self.credentials:
                    raise ValueError("Password grant type requires 'username' and 'password'")
                self.username = self.credentials['username']
                self.password = self.credentials['password']
            case 'authorization_code':
                if 'redirect_uri' not in self.credentials:
                    raise ValueError("Authorization code grant type requires 'redirect_uri'")
                self.redirect_uri = self.credentials['redirect_uri']
            case 'refresh_token':
                if 'refresh_token' not in self.credentials:
                    raise ValueError("Refresh token grant type requires 'refresh_token'")
                self.refresh_token = self.credentials['refresh_token']
            case _:
                raise ValueError(f"Unsupported grant type: {self.grant_type}. "
                                 f"Supported types are: {', '.join(self.SUPPORTED_GRANT_TYPES)}")

    async def authenticate(self) -> None:
        # Get initial token
        async with aiohttp.ClientSession() as session:
            data = {
                self.client_id_key: self.client_id,
                self.client_secret_key: self.client_secret,
            }

            if self.grant_type:
                data['grant_type'] = self.grant_type
                match self.grant_type:
                    case 'password':
                        data.update({
                            'username': self.username,
                            'password': self.password
                        })
                    case 'authorization_code':
                        data.update({
                            'code': self.credentials['code'],
                            'redirect_uri': self.redirect_uri
                        })
                    case 'refresh_token':
                        if not self.refresh_token:
                            raise ValueError("Refresh token grant type requires 'refresh_token'")
                        
                        data.update({
                            'refresh_token': self.refresh_token
                        })
                    case _:
                        raise ValueError(f"Unsupported grant type: {self.grant_type}. "
                                         f"Supported types are: {', '.join(self.SUPPORTED_GRANT_TYPES)}")

            if self.scope:
                data['scope'] = self.scope

            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get('error', error_text)
                    except:
                        error_msg = error_text
                    raise ValueError(f"Authentication failed: {error_msg}")
                
                token_data = await response.json()
                self.access_token = token_data[self.access_token_key]
                self.refresh_token = token_data.get(self.refresh_token_key, self.refresh_token)
                self.is_authenticated = True

    async def refresh(self) -> None:
        if not self.refresh_token:
            # No refresh token, get new access token
            await self.authenticate()
            return

        async with aiohttp.ClientSession() as session:
            data = {
                self.client_id_key: self.client_id,
                self.client_secret_key: self.client_secret,
            }
            
            if self.grant_type:
                data['grant_type'] = self.grant_type
                if self.grant_type == 'refresh_token':
                    data.update({
                        'refresh_token': self.refresh_token
                    })


            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get('error', error_text)
                    except:
                        error_msg = error_text
                    raise ValueError(f"Token refresh failed: {error_msg}")
                
                token_data = await response.json()
                self.access_token = token_data[self.access_token_key]
                self.refresh_token = token_data.get(self.refresh_token_key, self.refresh_token)
                self.is_authenticated = True

    def get_headers(self) -> Dict[str, str]:
        super().get_headers()  # Check authentication state
        return {'Authorization': f'Bearer {self.access_token}'} 