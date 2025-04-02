import json
import asyncio
from typing import Optional, Dict, Any
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.validation import Validator, ValidationError

from ...logging import BaseLogger
from ..session_store import SessionStore
from ..swagger import SwaggerParser, SwaggerParserError, SwaggerSpec

class URLValidator(Validator):
    """Validator for URLs."""
    
    def validate(self, document):
        """Validate that the input is a valid URL."""
        text = document.text
        if not text:
            raise ValidationError(message="URL cannot be empty")
        if not text.startswith(('http://', 'https://')):
            raise ValidationError(message="URL must start with http:// or https://")

class CreateSessionCommand:
    """Command class for creating new API sessions.
    
    This class handles the creation of new API sessions, including:
    - Base URL configuration
    - Authentication setup (bearer, basic, OAuth2, API key)
    - Optional Swagger/OpenAPI specification import
    - Authentication testing
    """
    
    AUTH_TYPES = ['bearer', 'basic', 'oauth2', 'api_key', 'none']
    
    def __init__(
        self,
        logger: BaseLogger,
        session_store: SessionStore,
    ):
        """
        Initialize the create session command.
        
        Args:
            logger: Logger instance
            session_store: Session store instance
        """
        self.logger = logger
        self.session_store = session_store
        self.url_validator = URLValidator()
        
    def create_session(self, name: str, interactive: bool = False):
        """
        Create a new session.
        
        Args:
            name: Name of the session
            interactive: Whether to run in interactive mode
        """
        if interactive:
            self.create_session_interactive(name)
        else:
            self.logger.log_error("Non-interactive mode not supported for session creation")
    
    def create_session_interactive(self, name: str):
        """Create a session in interactive mode."""
        # Create histories
        base_url_history = InMemoryHistory()
        auth_type_history = InMemoryHistory()
        auth_creds_history = InMemoryHistory()
        swagger_url_history = InMemoryHistory()
        
        # Create completers
        auth_type_completer = WordCompleter(self.AUTH_TYPES)
        
        try:
            # Get base URL
            base_url = prompt(
                "Base URL (e.g., https://api.example.com): ",
                validator=self.url_validator,
                history=base_url_history
            )
            
            # Ask about authentication
            auth_type = prompt(
                "Authentication type (bearer/basic/oauth2/api_key/none): ",
                completer=auth_type_completer,
                history=auth_type_history
            ).lower()
            
            # Handle authentication setup
            auth_credentials = None
            if auth_type != 'none':
                self.logger.log_info("\nAuthentication Setup:")
                if auth_type == 'bearer':
                    self.logger.log_info("Bearer token authentication")
                    token = prompt("Enter bearer token: ")
                    auth_credentials = {"token": token}
                    
                elif auth_type == 'basic':
                    self.logger.log_info("Basic authentication")
                    username = prompt("Enter username: ")
                    password = prompt("Enter password: ", is_password=True)
                    auth_credentials = {
                        "username": username,
                        "password": password
                    }
                    
                elif auth_type == 'oauth2':
                    self.logger.log_info("\n⚠️  OAuth2 Authentication Setup")
                    self.logger.log_info("Note: OAuth2 implementation varies across APIs. This setup provides basic support")
                    self.logger.log_info("and may need adjustments based on your specific API requirements.")
                    
                    # Required fields
                    client_id = prompt("Enter client ID: ")
                    client_secret = prompt("Enter client secret: ", is_password=True)
                    token_url = prompt("Enter token URL: ", validator=self.url_validator)
                    scope = prompt("Enter scope (optional): ")
                    
                    # Optional key mappings
                    self.logger.log_info("\nOptional: Configure custom key mappings (press Enter to use defaults)")
                    client_id_key = prompt("Client ID key (default: client_id): ", default="client_id")
                    client_secret_key = prompt("Client secret key (default: client_secret): ", default="client_secret")
                    access_token_key = prompt("Access token key (default: access_token): ", default="access_token")
                    refresh_token_key = prompt("Refresh token key (default: refresh_token): ", default="refresh_token")
                    
                    auth_credentials = {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "token_url": token_url,
                        "client_id_key": client_id_key,
                        "client_secret_key": client_secret_key,
                        "access_token_key": access_token_key,
                        "refresh_token_key": refresh_token_key
                    }
                    if scope:
                        auth_credentials["scope"] = scope
                    
                elif auth_type == 'api_key':
                    self.logger.log_info("API Key authentication")
                    api_key = prompt("Enter API key: ", is_password=True)
                    header_name = prompt("Enter header name (e.g., X-API-Key): ")
                    auth_credentials = {
                        "api_key": api_key,
                        "header_name": header_name
                    }
            
            # Ask about Swagger/OpenAPI
            has_swagger = prompt(
                "Do you want to import Swagger/OpenAPI specification? (y/N): ",
                default="N"
            ).lower() == 'y'
            
            swagger_spec_path = None
            if has_swagger:
                swagger_source = prompt(
                    "Enter Swagger URL or file path: ",
                    history=swagger_url_history
                )
                
                try:
                    # Parse specification
                    parser = SwaggerParser()
                    spec = parser.parse(swagger_source)
                    
                    # Validate specification
                    self.logger.log_info("Validating Swagger specification...")
                    SwaggerSpec.model_validate(spec)
                    self.logger.log_info("Swagger specification is valid")
                    
                    # Save parsed spec
                    swagger_spec_path = parser.save_swagger_spec(spec, name)
                    self.logger.log_info(f"Saved Swagger specification to {swagger_spec_path}")
                    self.logger.log_info(f"Found {len(spec.paths)} endpoints")
                    
                except Exception as e:
                    self.logger.log_error(f"Failed to import Swagger specification: {str(e)}")
                    if prompt("Continue without Swagger? (y/N): ", default="N").lower() != 'y':
                        return
            
            # Prepare session data
            session_data = {
                'base_url': base_url,
                'auth': {
                    'type': auth_type,
                    'credentials': auth_credentials
                } if auth_type != 'none' else None
            }
            
            if swagger_spec_path:
                session_data['swagger_spec_path'] = swagger_spec_path
            
            # Create session
            self.session_store.upsert_session(name, json.dumps(session_data))
            self.logger.log_info(f"\nSession '{name}' created successfully!")
            
            # Test authentication if configured
            if auth_type != 'none':
                if prompt("Test authentication? (y/N): ", default="N").lower() == 'y':
                    self.test_authentication(name)
            
        except KeyboardInterrupt:
            self.logger.log_info("\nSession creation cancelled")
        except Exception as e:
            self.logger.log_error(f"Failed to create session: {str(e)}")
    
    def test_authentication(self, name: str):
        """Test authentication for a session."""
        try:
            session = self.session_store.get_session(name)
            
            if not session.auth_config:
                self.logger.log_error(f"Session '{name}' has no authentication configured")
                return

            # Run the authentication test
            async def test_auth():
                try:
                    self.logger.log_info("Testing authentication...")
                    
                    # Authenticate if needed
                    if not session.is_authenticated():
                        await session.authenticate()
                    
                    # Get headers
                    headers = session.get_headers()
                    self.logger.log_info("\nAuthentication successful!")
                    self.logger.log_info("\nHeaders:")
                    for key, value in headers.items():
                        # Mask sensitive values
                        if key.lower() in {'authorization', 'x-api-key', 'api-key'}:
                            value = '*' * 8
                        self.logger.log_info(f"  {key}: {value}")
                except Exception as e:
                    self.logger.log_error(f"\nAuthentication failed: {str(e)}")

            # Run the async test
            asyncio.run(test_auth())
            
        except Exception as e:
            self.logger.log_error(f"Failed to test authentication: {str(e)}") 