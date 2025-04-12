import asyncio
import json
from typing import Optional, Dict, Any

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory

from ...logging import BaseLogger
from ...session.session_store import SessionStore
from ...session.session import Session
from ...session.swagger.client import SwaggerClient
from ..resilient_http_client import ResilientHttpClient, ResilientHttpClientConfig, HttpRequestSpec


class EndpointCompleter(Completer):
    """Completer for API endpoints based on Swagger spec."""
    
    def __init__(self, swagger_client: SwaggerClient, method: Optional[str] = None):
        """
        Initialize the endpoint completer.
        
        Args:
            swagger_client: Swagger client
            method: If provided, only show endpoints for this HTTP method
        """
        self.swagger_client = swagger_client
        self.method = method
        self.endpoints = swagger_client.get_available_endpoints(method)
        
    def get_completions(self, document: Document, complete_event):
        """Get completions for the current input."""
        word = document.text
        
        for endpoint in self.endpoints:
            path = endpoint['path']
            summary = endpoint.get('summary')
            
            # Get display text with path and description
            display = path
            if summary:
                display = f"{path} - {summary}"
                
            # Calculate similarity or match
            if word.lower() in path.lower():
                # Higher score for exact path starts
                yield Completion(
                    path,
                    start_position=-len(word),
                    display=display,
                    display_meta=endpoint['method']
                )


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
        backoff_factor: float = 0.5,
        max_delay: Optional[int] = None
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
            max_delay: Maximum delay between retries in seconds
        """
        self.logger = logger
        self.session_store = session_store
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
    
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
        # Log request details
        self.logger.log_info(f"\nRequest Details:")
        self.logger.log_info(f"Method: {method}")
        self.logger.log_info(f"Endpoint: {endpoint}")
        if headers:
            self.logger.log_info("Headers:")
            for key, value in headers.items():
                # Mask sensitive values
                if key.lower() in {'authorization', 'x-api-key', 'api-key'}:
                    value = '*' * 8
                self.logger.log_info(f"  {key}: {value}")
        if data:
            self.logger.log_info("Data:")
            self.logger.log_info(json.dumps(data, indent=2))
        
        # Create executor with session data and options
        executor = ResilientHttpClient(
            session=session,
            config=ResilientHttpClientConfig(
                timeout=self.timeout,
                verify_ssl=self.verify_ssl,
                max_retries=self.max_retries,
                backoff_factor=self.backoff_factor,
                max_delay=self.max_delay
            ),
            logger=self.logger
        )
        
        try:
            # Execute request
            response = await executor.execute_request(
                HttpRequestSpec(
                    method=method,
                    url=endpoint,
                    data=data,
                    headers=headers
                )
            )

            # Log response
            await self._log_response(response)
                
            return response
        except Exception as e:
            self.logger.log_error(f"\nRequest failed with error: {str(e)}")
            self.logger.log_error("Request details were logged above")
            raise
    
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
        
        # Get Swagger client if available
        swagger_client = session.swagger_client
        endpoint_completer = None
        
        if swagger_client:
            self.logger.log_info(f"Using Swagger specification: {swagger_client.api_title} {swagger_client.api_version}")
            if swagger_client.api_description:
                self.logger.log_info(swagger_client.api_description)
        
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
            
            # Update endpoint completer with selected method
            if swagger_client:
                endpoint_completer = EndpointCompleter(swagger_client, method)
                endpoints = swagger_client.get_available_endpoints(method)
                self.logger.log_info(f"Found {len(endpoints)} {method} endpoints")
                
            # Get endpoint
            try:
                endpoint = prompt(
                    "Endpoint: ",
                    completer=endpoint_completer,
                    history=endpoint_history
                )
                if not endpoint:
                    continue
            except KeyboardInterrupt:
                self.logger.log_info("Interactive mode exited")
                return
            
            # Handle path parameters if present
            if swagger_client:
                endpoint_details = swagger_client.get_endpoint_details(endpoint, method)
                if endpoint_details and 'path_params' in endpoint_details:
                    path_params = endpoint_details['path_params']
                    if path_params:
                        self.logger.log_info(f"Path parameters found: {', '.join(path_params.keys())}")
                        # Prompt for each path parameter
                        for param_name, param_value in path_params.items():
                            try:
                                value = prompt(
                                    f"Enter {param_name}: ",
                                    default=param_value if param_value else ""
                                )
                                if not value:
                                    self.logger.log_error(f"Path parameter {param_name} is required")
                                    continue
                                # Replace the parameter in the endpoint
                                endpoint = endpoint.replace(f"{{{param_name}}}", value)
                            except KeyboardInterrupt:
                                self.logger.log_info("Interactive mode exited")
                                return
            
            # Get suggestions for data and headers from Swagger if available
            sample_data = None
            sample_headers = None
            
            if swagger_client:
                # Get samples
                sample_data = swagger_client.get_request_sample(endpoint, method)
                sample_headers = swagger_client.get_header_samples(endpoint, method)
                
                # Log samples if available
                if sample_data:
                    self.logger.log_info(f"Sample request data: {json.dumps(sample_data, indent=2)}")
                if sample_headers:
                    self.logger.log_info(f"Sample headers: {json.dumps(sample_headers, indent=2)}")
                
                # Validate the endpoint
                is_valid, errors = swagger_client.validate_request(endpoint, method)
                if not is_valid:
                    self.logger.log_error(f"Endpoint validation warnings: {', '.join(errors)}")
            
            # Get data for non-GET requests
            data = None
            if method != 'GET':
                try:
                    # Show sample data if available
                    sample_prompt = ""
                    if sample_data:
                        sample_prompt = f" (Sample available)"
                        
                    data_str = prompt(
                        f"Request data (JSON, press Enter to skip){sample_prompt}: ",
                        history=data_history,
                        default=json.dumps(sample_data) if sample_data else ""
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
                    history=headers_history,
                    default=json.dumps(sample_headers) if sample_headers else ""
                )
                if headers_str:
                    try:
                        headers = json.loads(headers_str)
                    except json.JSONDecodeError:
                        self.logger.log_error("Invalid JSON headers, skipping")
                        headers = None
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
                continue
            
            # Ask if user wants to make another request
            try:
                response = prompt(
                    "Make another request? (y/N): ",
                    default="N"
                ).lower()
                if response != 'y':
                    break
            except KeyboardInterrupt:
                break
                
        self.logger.log_info("Interactive mode exited")