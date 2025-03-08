import click
import json
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
    def create(name: str, base_url: str, auth_type: str | None = None,
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
            session_store = SessionStore()
            
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
            click.echo(f"Session '{name}' created successfully")
            
        except Exception as e:
            click.echo(f"Error: {str(e)}", err=True)

    @session.command(name='list')
    def list_sessions() -> None:
        """List all available sessions."""
        try:
            session_store = SessionStore()
            sessions = session_store.list_sessions()
            
            if not sessions:
                click.echo("No sessions found")
                return
                
            for name, session in sessions.items():
                click.echo(f"\nSession: {name}")
                click.echo(f"Base URL: {session.base_url}")
                if session.auth_config:
                    click.echo(f"Auth Type: {session.auth_config.type}")
                    
        except Exception as e:
            click.echo(f"Error: {str(e)}", err=True)

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
    def update(name: str, new_name: str | None = None, base_url: str | None = None,
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
            session_store = SessionStore()
            sessions = session_store.list_sessions()
            
            if name not in sessions:
                click.echo(f"Session '{name}' not found")
                return
            
            # Get current session data
            current_session = sessions[name]
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
            click.echo(f"Session '{name}' updated successfully")
            
        except Exception as e:
            click.echo(f"Error: {str(e)}", err=True)

    @session.command(name='delete')
    @click.argument('name')
    def delete(name: str) -> None:
        """Delete a session."""
        try:
            session_store = SessionStore()
            session_store.delete_session(name)
            click.echo(f"Session '{name}' deleted successfully")
            
        except Exception as e:
            click.echo(f"Error: {str(e)}", err=True)

    @session.command(name='show')
    @click.argument('name')
    def show(name: str) -> None:
        """Show details of a specific session."""
        try:
            session_store = SessionStore()
            sessions = session_store.list_sessions()
            
            if name not in sessions:
                click.echo(f"Session '{name}' not found")
                return
                
            session = sessions[name]
            click.echo(f"Session: {name}")
            click.echo(f"Base URL: {session.base_url}")
            
            if session.auth_config:
                click.echo("\nAuthentication:")
                click.echo(f"  Type: {session.auth_config.type}")
                click.echo("  Credentials:")
                for key, value in session.auth_config.credentials.items():
                    # Mask sensitive values
                    if key in {'token', 'password', 'client_secret'}:
                        value = '*' * 8
                    click.echo(f"    {key}: {value}")
                    
        except Exception as e:
            click.echo(f"Error: {str(e)}", err=True)

    return session 