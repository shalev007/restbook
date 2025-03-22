import asyncio
import aiohttp
import click
from typing import Optional, Dict, Any
from ..logging import BaseLogger
from ..session.session_store import SessionStore
from .executor import RequestExecutor
import json
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory


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
    
    async def execute_request(
        session, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        logger: Optional[BaseLogger] = None
    ):
        """Execute a request and log the response."""
        # Create executor with session data and options
        executor = RequestExecutor(
            session=session,
            timeout=timeout,
            verify_ssl=verify_ssl,
            max_retries=max_retries,
            backoff_factor=backoff_factor
        )
        
        # Execute request
        response = await executor.execute_request(
            method=method,
            endpoint=endpoint,
            data=data,
            headers=headers
        )

        if logger:
            await log_response(response, logger)
            
        return response
    
    def run_interactive_mode(ctx, session_name, timeout, no_verify_ssl, max_retries, backoff_factor):
        """Run the interactive request mode using prompt_toolkit."""
        logger: BaseLogger = ctx.obj.logger
        session_store: SessionStore = ctx.obj.session_store
        
        # Get session
        try:
            session = session_store.get_session(session_name)
        except Exception as e:
            logger.log_error(f"Error getting session: {str(e)}")
            return
            
        # Create completers
        method_completer = WordCompleter(['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
        
        # Create histories
        method_history = InMemoryHistory()
        endpoint_history = InMemoryHistory()
        data_history = InMemoryHistory()
        headers_history = InMemoryHistory()
        
        # Check if session has swagger for better completion
        has_swagger = session.has_swagger()
        if has_swagger:
            logger.log_info("Using Swagger specification for endpoint suggestions")
            # TODO: Implement Swagger-based completion
        
        while True:
            # Get method
            try:
                method = prompt(
                    "Method (GET/POST/PUT/DELETE/PATCH): ",
                    completer=method_completer,
                    history=method_history
                ).upper()
                if not method:
                    continue
                if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    logger.log_error(f"Invalid method: {method}")
                    continue
            except KeyboardInterrupt:
                logger.log_info("Interactive mode exited")
                return
                
            # Get endpoint
            try:
                endpoint = prompt(
                    "Endpoint: ",
                    history=endpoint_history
                )
                if not endpoint:
                    continue
            except KeyboardInterrupt:
                logger.log_info("Interactive mode exited")
                return
                
            # Get data for non-GET requests
            data = None
            if method != 'GET':
                try:
                    data_str = prompt(
                        "Request data (JSON, press Enter to skip): ",
                        history=data_history
                    )
                    if data_str:
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.log_error("Invalid JSON data, sending as raw string")
                            data = data_str
                except KeyboardInterrupt:
                    logger.log_info("Interactive mode exited")
                    return
            
            # Get headers
            headers = None
            try:
                headers_str = prompt(
                    "Headers (JSON, press Enter to skip): ",
                    history=headers_history
                )
                if headers_str:
                    try:
                        headers = json.loads(headers_str)
                    except json.JSONDecodeError:
                        logger.log_error("Invalid JSON headers, continuing without headers")
            except KeyboardInterrupt:
                logger.log_info("Interactive mode exited")
                return
                
            # Execute request
            try:
                logger.log_info(f"Executing {method} request to {endpoint}")
                asyncio.run(execute_request(
                    session=session,
                    method=method,
                    endpoint=endpoint,
                    data=data,
                    headers=headers,
                    timeout=timeout,
                    verify_ssl=not no_verify_ssl,
                    max_retries=max_retries,
                    backoff_factor=backoff_factor,
                    logger=logger
                ))
            except Exception as e:
                logger.log_error(f"Error executing request: {str(e)}")
            
            # Ask if user wants to make another request
            try:
                if not click.confirm("Make another request?"):
                    break
            except KeyboardInterrupt:
                break
                
        logger.log_info("Interactive mode exited")

    @click.command()
    @click.argument("session_name")
    @click.argument("method", type=click.Choice(['GET', 'POST', 'PUT', 'DELETE', 'PATCH']), required=False)
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
        logger: BaseLogger = ctx.obj.logger
        session_store: SessionStore = ctx.obj.session_store
        
        # Run in interactive mode if flag is set
        if interactive:
            run_interactive_mode(ctx, session_name, timeout, no_verify_ssl, max_retries, backoff_factor)
            return
            
        # Ensure method and endpoint are provided in non-interactive mode
        if not method or not endpoint:
            logger.log_error("Method and endpoint are required in non-interactive mode")
            return
        
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
        
        # Execute request
        asyncio.run(execute_request(
            session=session,
            method=method,
            endpoint=endpoint,
            data=_data,
            headers=_headers,
            timeout=timeout,
            verify_ssl=not no_verify_ssl,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            logger=logger
        ))

    return request 