import asyncio
import click
from typing import Optional
from ..logging import BaseLogger
from ..session.session_store import SessionStore
from .executor import RequestExecutor


def create_request_commands() -> click.Command:
    """Create the request command."""
    @click.command()
    @click.argument("session_name")
    @click.argument("method", type=click.Choice(['GET', 'POST', 'PUT', 'DELETE', 'PATCH']))
    @click.argument("endpoint")
    @click.option("--data", help="JSON data to send with the request")
    @click.option("--headers", help="Additional headers in JSON format")
    @click.option("--timeout", type=int, default=30, help="Request timeout in seconds")
    @click.option("--no-verify-ssl", is_flag=True, help="Disable SSL verification")
    @click.option("--max-retries", type=int, default=3, help="Maximum number of retries")
    @click.option("--backoff-factor", type=float, default=0.5, help="Backoff factor for retries")
    @click.pass_context
    def request(
        ctx,
        session_name: str,
        method: str,
        endpoint: str,
        data: Optional[str],
        headers: Optional[str],
        timeout: int,
        no_verify_ssl: bool,
        max_retries: int,
        backoff_factor: float
    ):
        """Make an HTTP request using a specified session."""
        logger: BaseLogger = ctx.obj.logger
        session_store: SessionStore = ctx.obj.session_store
        
        # Get session data
        sessions = session_store.list_sessions()
        if session_name not in sessions:
            error_msg = f"Session '{session_name}' does not exist."
            logger.log_error(error_msg)
            raise ValueError(error_msg)
        session = sessions[session_name]
        
        # Create executor with session data and options
        executor = RequestExecutor(
            base_url=session.base_url,
            session=session,
            logger=logger,
            timeout=timeout,
            verify_ssl=not no_verify_ssl,
            max_retries=max_retries,
            backoff_factor=backoff_factor
        )
        
        # Execute request
        asyncio.run(executor.execute_request(method, endpoint, data, headers))

    return request 