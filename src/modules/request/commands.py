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
    @click.pass_context
    def request(ctx, session_name: str, method: str, endpoint: str, data: Optional[str], headers: Optional[str]):
        """Make an HTTP request using a specified session."""
        logger: BaseLogger = ctx.obj.logger
        session_store: SessionStore = ctx.obj.session_store
        
        executor = RequestExecutor(session_store, logger)
        executor.execute_request(session_name, method, endpoint, data, headers)

    return request 