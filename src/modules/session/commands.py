import click
import json
from typing import Optional
from ..logging import BaseLogger
from .session_store import SessionStore


def create_session_commands() -> click.Group:
    """Create the session command group."""
    @click.group()
    def session():
        """Manage API sessions (create, list, update, delete)."""
        pass

    @session.command()
    @click.argument("name")
    @click.option("--base-url", prompt="Base URL", help="The API base URL.")
    @click.option("--token", help="Authentication token for the API.", default=None)
    @click.pass_context
    def create(ctx, name: str, base_url: str, token: Optional[str]):
        """Create a new session."""
        logger: BaseLogger = ctx.obj.logger
        session_store: SessionStore = ctx.obj.session_store
        try:
            new_session = session_store.create_session(name, base_url, token)
            logger.log_info(f"Session '{name}' created successfully:")
            logger.log_info(json.dumps(new_session.to_dict(), indent=2))
        except ValueError as err:
            logger.log_error(str(err))

    @session.command(name="list")
    @click.pass_context
    def list_sessions(ctx):
        """List all available sessions."""
        logger: BaseLogger = ctx.obj.logger
        session_store: SessionStore = ctx.obj.session_store
        sessions = session_store.list_sessions()
        if not sessions:
            logger.log_info("No sessions found.")
        else:
            for session in sessions.values():
                logger.log_info(json.dumps(session.to_dict(), indent=2))

    @session.command()
    @click.argument("name")
    @click.option("--base-url", help="New API base URL.", default=None)
    @click.option("--token", help="New authentication token.", default=None)
    @click.pass_context
    def update(ctx, name: str, base_url: Optional[str], token: Optional[str]):
        """Update an existing session."""
        logger: BaseLogger = ctx.obj.logger
        session_store: SessionStore = ctx.obj.session_store
        try:
            updated_session = session_store.update_session(name, base_url, token)
            logger.log_info(f"Session '{name}' updated successfully:")
            logger.log_info(json.dumps(updated_session.to_dict(), indent=2))
        except ValueError as err:
            logger.log_error(str(err))

    @session.command()
    @click.argument("name")
    @click.pass_context
    def delete(ctx, name: str):
        """Delete an existing session."""
        logger: BaseLogger = ctx.obj.logger
        session_store: SessionStore = ctx.obj.session_store
        try:
            session_store.delete_session(name)
            logger.log_info(f"Session '{name}' deleted successfully.")
        except ValueError as err:
            logger.log_error(str(err))

    return session 