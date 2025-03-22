import asyncio
import json
import click
from typing import Optional, Dict, Any, List

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory

from ...logging import BaseLogger
from ...session.session_store import SessionStore
from ...session.session import Session
from ..executor import RequestExecutor


class RequestCommand:
    """Command class for handling HTTP requests."""
    
    SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
    
    def __init__(
        self,
        logger: BaseLogger,
        session_store: SessionStore,
        timeout: int = 30,
        verify_ssl: bool = True,
        max_retries: int = 3,
        backoff_factor: float = 0.5
    ):
        """
        Initialize the request command.
        
        Args:
            logger: Logger instance
            session_store: Session store instance
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retries
            backoff_factor: Backoff factor for retries
        """
        self.logger = logger
        self.session_store = session_store
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    async def execute_request(
        self,
        session: Session, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Execute a request and log the response.
        
        Args:
            session: Session to use for the request
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data
            headers: Request headers
            
        Returns:
            The response from the API
        """
        # Create executor with session data and options
        executor = RequestExecutor(
            session=session,
            timeout=self.timeout,
            verify_ssl=self.verify_ssl,
            max_retries=self.max_retries,
            backoff_factor=self.backoff_factor
        )
        
        # Execute request
        response = await executor.execute_request(
            method=method,
            endpoint=endpoint,
            data=data,
            headers=headers
        )

        # Log response
        await self._log_response(response)
            
        return response
    
    async def _log_response(self, response):
        """Log the response details."""
        self.logger.log_status(response.status)
        try:
            body = await response.json()
            body_str = json.dumps(body, indent=2)
        except:
            body_str = await response.text()
        self.logger.log_body(body_str)
    
    def get_session(self, session_name: str) -> Session:
        """Get a session by name."""
        try:
            return self.session_store.get_session(session_name)
        except Exception as e:
            self.logger.log_error(f"Error getting session: {str(e)}")
            raise
    
    def run(
        self,
        session_name: str,
        method: Optional[str] = None,
        endpoint: Optional[str] = None,
        data: Optional[str] = None,
        headers: Optional[str] = None,
        interactive: bool = False
    ):
        """
        Run the request command.
        
        Args:
            session_name: Name of the session to use
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data in JSON format
            headers: Request headers in JSON format
            interactive: Whether to run in interactive mode
        """
        # Get session
        try:
            session = self.get_session(session_name)
        except Exception:
            return
        
        # Choose mode
        if interactive:
            self.run_interactive_mode(session)
        else:
            self.run_standard_mode(session, method, endpoint, data, headers)
    
    def run_standard_mode(
        self, 
        session: Session, 
        method: Optional[str],
        endpoint: Optional[str],
        data: Optional[str],
        headers: Optional[str]
    ):
        """Run the command in standard (non-interactive) mode."""
        # Ensure method and endpoint are provided
        if not method or not endpoint:
            self.logger.log_error("Method and endpoint are required in non-interactive mode")
            return
        
        # Parse data
        parsed_data = None
        if data:
            try:
                parsed_data = json.loads(data)
            except json.JSONDecodeError:
                self.logger.log_error(f"Invalid JSON data: {data}")
                return
        
        # Parse headers
        parsed_headers = None
        if headers:
            try:
                parsed_headers = json.loads(headers)
            except json.JSONDecodeError:
                self.logger.log_error(f"Invalid JSON headers: {headers}")
                return
        
        # Execute request
        asyncio.run(self.execute_request(
            session=session,
            method=method,
            endpoint=endpoint,
            data=parsed_data,
            headers=parsed_headers
        ))
    
    def run_interactive_mode(self, session: Session):
        """Run the command in interactive mode."""
        # Create completers
        method_completer = WordCompleter(self.SUPPORTED_METHODS)
        
        # Create histories
        method_history = InMemoryHistory()
        endpoint_history = InMemoryHistory()
        data_history = InMemoryHistory()
        headers_history = InMemoryHistory()
        
        # Check if session has swagger for better completion
        has_swagger = session.has_swagger()
        if has_swagger:
            self.logger.log_info("Using Swagger specification for endpoint suggestions")
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
                if method not in self.SUPPORTED_METHODS:
                    self.logger.log_error(f"Invalid method: {method}")
                    continue
            except KeyboardInterrupt:
                self.logger.log_info("Interactive mode exited")
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
                self.logger.log_info("Interactive mode exited")
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
                            self.logger.log_error("Invalid JSON data, sending as raw string")
                            data = data_str
                except KeyboardInterrupt:
                    self.logger.log_info("Interactive mode exited")
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
                        self.logger.log_error("Invalid JSON headers, continuing without headers")
            except KeyboardInterrupt:
                self.logger.log_info("Interactive mode exited")
                return
                
            # Execute request
            try:
                self.logger.log_info(f"Executing {method} request to {endpoint}")
                asyncio.run(self.execute_request(
                    session=session,
                    method=method,
                    endpoint=endpoint,
                    data=data,
                    headers=headers
                ))
            except Exception as e:
                self.logger.log_error(f"Error executing request: {str(e)}")
            
            # Ask if user wants to make another request
            try:
                if not click.confirm("Make another request?"):
                    break
            except KeyboardInterrupt:
                break
                
        self.logger.log_info("Interactive mode exited")