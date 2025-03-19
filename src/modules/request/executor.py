import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, NoReturn, List
from aiohttp import ClientTimeout
from ..logging import BaseLogger
from ..session.session import Session


class RequestExecutor:
    """Handles HTTP request execution and response processing."""
    
    # Status codes that should trigger retries
    RETRY_STATUS_CODES: List[int] = [429, 500, 502, 503, 504]
    
    # Status codes that might indicate auth issues
    AUTH_STATUS_CODES: List[int] = [401, 403]
    
    def __init__(
        self,
        session: Session,
        timeout: int = 30,
        verify_ssl: bool = True,
        max_retries: int = 3,
        backoff_factor: float = 0.5
    ):
        """Initialize the request executor.
        
        Args:
            session: Session object containing base URL and authentication details
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retries for failed requests
            backoff_factor: Backoff factor between retries
        """
        self.session = session
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
        # Configure timeout
        self.client_timeout = ClientTimeout(total=timeout)

    async def execute_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> aiohttp.ClientResponse:
        """Execute an HTTP request asynchronously.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Optional dictionary of data to send with the request
            headers: Optional dictionary of additional headers
            
        Returns:
            aiohttp.ClientResponse: The response from the server
            
        Raises:
            aiohttp.ClientError: If the request fails after max retries
        """
        # Prepare the request
        url = self._build_url(endpoint)
        
        # Create client session with retry logic
        async with aiohttp.ClientSession(timeout=self.client_timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    # Get fresh headers for each attempt in case of auth refresh
                    request_headers = await self._prepare_headers(headers)
                    
                    # Make the request
                    response = await client.request(
                        method=method,
                        url=url,
                        json=data,  # data is already a dict
                        headers=request_headers,
                        ssl=self.verify_ssl
                    )
                    
                    # Wait for the response body to be fully received
                    await response.read()
                    
                    # Handle authentication errors
                    if response.status in self.AUTH_STATUS_CODES and attempt < self.max_retries:
                        if await self._handle_auth_retry():
                            continue
                    
                    # Check if we should retry other errors
                    if response.status in self.RETRY_STATUS_CODES and attempt < self.max_retries:
                        await self._handle_retry_delay(attempt)
                        continue
                    
                    return response
                    
                except aiohttp.ClientError as err:
                    if attempt < self.max_retries:
                        await self._handle_retry_delay(attempt)
                        continue
                    raise err

            raise aiohttp.ClientError("Max retries exceeded")

    def _build_url(self, endpoint: str) -> str:
        """Build the full URL for the request.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            str: Full URL including base URL and endpoint
        """
        return f"{self.session.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    async def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare request headers.
        
        Args:
            headers: Optional dictionary of additional headers to include
            
        Returns:
            Dict[str, str]: Combined headers including authentication
        """
        request_headers = {}
        if not self.session.is_authenticated():
            await self.session.authenticate()
        request_headers = self.session.get_headers()
        if headers:
            request_headers.update(headers)
        return request_headers

    async def _handle_auth_retry(self) -> bool:
        """Handle authentication retry logic.
        
        Returns:
            bool: True if retry should continue, False otherwise
        """
        try:
            # Try to refresh first
            await self.session.refresh_auth()
            return True
        except Exception:
            # If refresh fails, try re-authenticating
            try:
                await self.session.authenticate()
                return True
            except Exception:
                # Both refresh and re-auth failed
                return False

    async def _handle_retry_delay(self, attempt: int) -> None:
        """Handle exponential backoff delay between retries.
        
        Args:
            attempt: Current retry attempt number
        """
        delay = self.backoff_factor * (2 ** attempt)
        await asyncio.sleep(delay)

    def _prepare_data(self, data: Optional[str]) -> Optional[Dict[str, Any]]:
        """Prepare request data.
        
        Args:
            data: JSON string to convert to dictionary
            
        Returns:
            Optional[Dict[str, Any]]: Parsed JSON data as dictionary
            
        Raises:
            ValueError: If data is not valid JSON
        """
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise ValueError("Data must be in valid JSON format") 