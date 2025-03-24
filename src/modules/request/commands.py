from typing import Optional
import click

from src.modules.request.command.request import RequestCommand

def create_request_commands() -> click.Command:
    """Create the request command."""

    @click.command(name="request")
    @click.argument("session_name")
    @click.argument("method", type=click.Choice(RequestCommand.SUPPORTED_METHODS), required=False)
    @click.argument("endpoint", required=False)
    @click.option("--data", help="JSON data to send with the request")
    @click.option("--headers", help="Additional headers in JSON format")
    @click.option("--timeout", type=int, default=30, help="Request timeout in seconds")
    @click.option("--no-verify-ssl", is_flag=True, help="Disable SSL verification")
    @click.option("--max-retries", type=int, default=3, help="Maximum number of retries")
    @click.option("--backoff-factor", type=float, default=0.5, help="Backoff factor for retries")
    @click.option("-i", "--interactive", is_flag=True, help="Run in interactive mode")
    @click.pass_context
    def request(
        ctx,
        session_name: str,
        method: Optional[str],
        endpoint: Optional[str],
        data: Optional[str],
        headers: Optional[str],
        timeout: int,
        no_verify_ssl: bool,
        max_retries: int,
        backoff_factor: float,
        interactive: bool
    ):
        """Make an HTTP request using a specified session.
        
        In interactive mode (-i/--interactive), you'll be prompted for method, endpoint, data, and headers.
        In non-interactive mode, method and endpoint are required arguments.
        """
        # Create command instance
        command = RequestCommand(
            logger=ctx.obj.logger,
            session_store=ctx.obj.session_store,
            timeout=timeout,
            verify_ssl=not no_verify_ssl,
            max_retries=max_retries,
            backoff_factor=backoff_factor
        )
        
        # Run the command
        command.run(
            session_name=session_name,
            method=method,
            endpoint=endpoint,
            data=data,
            headers=headers,
            interactive=interactive
        )

    return request