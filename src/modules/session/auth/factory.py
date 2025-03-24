from typing import Dict, Type
from .base import Authenticator, AuthConfig
from .bearer import BearerAuthenticator
from .basic import BasicAuthenticator
from .oauth2 import OAuth2Authenticator
from .api_key import ApiKeyAuthenticator


def create_authenticator(config: AuthConfig) -> Authenticator:
    """Create an authenticator based on the auth type."""
    auth_types: Dict[str, Type[Authenticator]] = {
        'bearer': BearerAuthenticator,
        'basic': BasicAuthenticator,
        'oauth2': OAuth2Authenticator,
        'api_key': ApiKeyAuthenticator,
    }
    
    if config.type not in auth_types:
        raise ValueError(f"Unsupported authentication type: {config.type}")
    
    return auth_types[config.type](config.credentials) 