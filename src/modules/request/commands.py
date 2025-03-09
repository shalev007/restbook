import asyncio
import aiohttp
import click
from typing import Optional
from ..logging import BaseLogger
from ..session.session_store import SessionStore
from .executor import RequestExecutor
import json


async def log_response(response: aiohttp.ClientResponse, logger: BaseLogger) -> None:
    """Log the response for a step."""
    logger.log_status(response.status)
    try:
        body = await response.json()
        body_str = json.dumps(body, indent=2)
    except:
        body_str = await response.text()
    logger.log_body(body_str)


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
        session = session_store.get_session(session_name)
        try:
            _data = json.loads(data) if data else None
        except json.JSONDecodeError:
            logger.log_error(f"Invalid JSON data: {data}")
            return
    
        try:
            _headers = json.loads(headers) if headers else None
        except json.JSONDecodeError:
            logger.log_error(f"Invalid JSON headers: {headers}")
            return
        
        # Create executor with session data and options
        executor = RequestExecutor(
            session=session,
            timeout=timeout,
            verify_ssl=not no_verify_ssl,
            max_retries=max_retries,
            backoff_factor=backoff_factor
        )
        
        # Execute request
        response =asyncio.run(executor.execute_request(
            method=method,
            endpoint=endpoint,
            data=_data,
            headers=_headers
        ))

        asyncio.run(log_response(response, logger))

    return request 