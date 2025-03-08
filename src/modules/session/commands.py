import click
import json
import asyncio
from typing import Dict, Any
from ..logging import BaseLogger
from .session_store import SessionStore


def create_session_commands() -> click.Group:
    """Create the session command group."""
    
    @click.group(name='session')
    def session():
        """Manage API sessions."""
        pass

    @session.command(name='create')
    @click.argument('name')
    @click.argument('base_url')
    @click.option('--auth-type', 
                 type=click.Choice(['bearer', 'basic', 'oauth2']),
                 help='Authentication type')
    @click.option('--auth-credentials',
                 help='Authentication credentials as JSON string. Examples:\n'
                      'Bearer: {"token": "my-token"}\n'
                      'Basic: {"username": "user", "password": "pass"}\n'
                      'OAuth2: {"client_id": "id", "client_secret": "secret", '
                      '"token_url": "https://auth.example.com/token", '
                      '"scope": "read write"}')
    @click.pass_context
    def create(ctx, name: str, base_url: str, auth_type: str | None = None,
               auth_credentials: str | None = None) -> None:
        """
        Create a new session.
        
        Examples:
            # Create a session without authentication
            restbook session create my-api https://api.example.com
            
            # Create a session with bearer token
            restbook session create my-api https://api.example.com \\
                --auth-type bearer \\
                --auth-credentials '{"token": "my-token"}'
            
            # Create a session with basic auth
            restbook session create my-api https://api.example.com \\
                --auth-type basic \\
                --auth-credentials '{"username": "user", "password": "pass"}'
            
            # Create a session with OAuth2
            restbook session create my-api https://api.example.com \\
                --auth-type oauth2 \\
                --auth-credentials '{
                    "client_id": "id",
                    "client_secret": "secret",
                    "token_url": "https://auth.example.com/token",
                    "scope": "read write"
                }'
        """
        try:
            session_store: SessionStore = ctx.obj.session_store
            logger: BaseLogger = ctx.obj.logger
            
            # Prepare session data
            session_data = {
                'base_url': base_url,
                'auth': {
                    'type': auth_type,
                    'credentials': json.loads(auth_credentials)
                } if auth_type and auth_credentials else None
            }
            
            # Create session
            session_store.upsert_session(name, json.dumps(session_data))
            logger.log_info(f"Session '{name}' created successfully")
            
        except Exception as e:
            logger.log_error(str(e))

    @session.command(name='list')
    @click.pass_context
    def list_sessions(ctx) -> None:
        """List all available sessions."""
        try:
            session_store: SessionStore = ctx.obj.session_store
            logger: BaseLogger = ctx.obj.logger
            sessions = session_store.list_sessions()
            
            if not sessions:
                logger.log_info("No sessions found")
                return
                
            for name, session in sessions.items():
                logger.log_info(f"\nSession: {name}")
                logger.log_info(f"Base URL: {session.base_url}")
                if session.auth_config:
                    logger.log_info(f"Auth Type: {session.auth_config.type}")
                    
        except Exception as e:
            logger.log_error(str(e))

    @session.command(name='update')
    @click.argument('name')
    @click.option('--new-name', help='New name for the session')
    @click.option('--base-url', help='New base URL for the API')
    @click.option('--auth-type', 
                 type=click.Choice(['bearer', 'basic', 'oauth2', 'none']),
                 help='New authentication type (use "none" to remove authentication)')
    @click.option('--auth-credentials',
                 help='New authentication credentials as JSON string. Examples:\n'
                      'Bearer: {"token": "my-token"}\n'
                      'Basic: {"username": "user", "password": "pass"}\n'
                      'OAuth2: {"client_id": "id", "client_secret": "secret", '
                      '"token_url": "https://auth.example.com/token", '
                      '"scope": "read write"}')
    @click.pass_context
    def update(ctx, name: str, new_name: str | None = None, base_url: str | None = None,
               auth_type: str | None = None, auth_credentials: str | None = None) -> None:
        """
        Update an existing session.
        
        Examples:
            # Update session name
            restbook session update old-name --new-name new-name
            
            # Update base URL
            restbook session update my-api --base-url https://new-api.example.com
            
            # Update authentication
            restbook session update my-api \\
                --auth-type bearer \\
                --auth-credentials '{"token": "new-token"}'
            
            # Remove authentication
            restbook session update my-api --auth-type none
            
            # Update multiple attributes
            restbook session update my-api \\
                --new-name new-api \\
                --base-url https://new-api.example.com \\
                --auth-type basic \\
                --auth-credentials '{"username": "new-user", "password": "new-pass"}'
        """
        try:
            session_store: SessionStore = ctx.obj.session_store
            logger: BaseLogger = ctx.obj.logger
            
            # Get current session
            current_session = session_store.get_session(name)
            
            # Prepare updated session data
            session_data: Dict[str, Any] = {
                'base_url': base_url or current_session.base_url,
                'auth': None
            }
            
            # Update authentication if specified
            if auth_type == 'none':
                session_data['auth'] = None
            elif auth_type or auth_credentials:
                current_auth = current_session.auth_config
                session_data['auth'] = {
                    'type': auth_type or (current_auth.type if current_auth else None),
                    'credentials': json.loads(auth_credentials) if auth_credentials else 
                                 (current_auth.credentials if current_auth else None)
                }
            else:
                session_data['auth'] = None if current_session.auth_config is None else {
                    'type': current_session.auth_config.type,
                    'credentials': current_session.auth_config.credentials
                }
            
            # Delete old session if name is changing
            if new_name:
                session_store.delete_session(name)
                name = new_name
            
            # Create/update session
            session_store.upsert_session(name, json.dumps(session_data), overwrite=True)
            logger.log_info(f"Session '{name}' updated successfully")
            
        except Exception as e:
            logger.log_error(str(e))

    @session.command(name='delete')
    @click.argument('name')
    @click.pass_context
    def delete(ctx, name: str) -> None:
        """Delete a session."""
        try:
            session_store: SessionStore = ctx.obj.session_store
            logger: BaseLogger = ctx.obj.logger
            session_store.delete_session(name)
            logger.log_info(f"Session '{name}' deleted successfully")
            
        except Exception as e:
            logger.log_error(str(e))

    @session.command(name='show')
    @click.argument('name')
    @click.pass_context
    def show(ctx, name: str) -> None:
        """Show details of a specific session."""
        try:
            session_store: SessionStore = ctx.obj.session_store
            logger: BaseLogger = ctx.obj.logger
            
            # Get session
            session = session_store.get_session(name)
            
            # Display session info
            logger.log_info(f"Session: {name}")
            logger.log_info(f"Base URL: {session.base_url}")
            
            if session.auth_config:
                logger.log_info("\nAuthentication:")
                logger.log_info(f"  Type: {session.auth_config.type}")
                logger.log_info("  Credentials:")
                for key, value in session.auth_config.credentials.items():
                    # Mask sensitive values
                    if key in {'token', 'password', 'client_secret'}:
                        value = '*' * 8
                    logger.log_info(f"    {key}: {value}")
                    
        except Exception as e:
            logger.log_error(str(e))

    @session.command(name='authenticate')
    @click.argument('name')
    @click.pass_context
    def authenticate(ctx, name: str) -> None:
        """
        Test authentication for a session.
        
        Examples:
            # Test authentication for a session
            restbook session authenticate my-api
        """
        try:
            session_store: SessionStore = ctx.obj.session_store
            logger: BaseLogger = ctx.obj.logger
            
            # Get session
            session = session_store.get_session(name)
            
            if not session.auth_config:
                logger.log_error(f"Session '{name}' has no authentication configured")
                return

            # Run the authentication test
            async def test_auth():
                try:
                    logger.log_info("Testing authentication...")
                    
                    # Authenticate if needed
                    if not session.is_authenticated():
                        await session.authenticate()
                    
                    # Get headers
                    headers = session.get_headers()
                    logger.log_info("\nAuthentication successful!")
                    logger.log_info("\nHeaders:")
                    for key, value in headers.items():
                        # Mask the actual token in the output
                        if key.lower() == 'authorization':
                            parts = value.split(' ')
                            if len(parts) > 1:
                                value = f"{parts[0]} {'*' * 8}"
                        logger.log_info(f"  {key}: {value}")
                except Exception as e:
                    logger.log_error(f"\nAuthentication failed: {str(e)}")

            # Run the async test
            asyncio.run(test_auth())
            
        except Exception as e:
            logger.log_error(str(e))

    return session 