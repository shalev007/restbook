import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, NoReturn
from aiohttp import ClientTimeout
from ..logging import BaseLogger
from ..session.session import Session


class RequestExecutor:
    """Handles HTTP request execution and response processing."""
    
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

    def _raise_error(self, err: Exception) -> NoReturn:
        """Helper method to raise errors."""
        raise err

    async def execute_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[str] = None,
        headers: Optional[str] = None
    ) -> aiohttp.ClientResponse:
        """Execute an HTTP request asynchronously.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Optional JSON data to send with the request
            headers: Optional JSON string of additional headers
            
        Returns:
            aiohttp.ClientResponse: The response from the server
            
        Raises:
            ValueError: If the headers or data are invalid JSON
            aiohttp.ClientError: If the request fails
        """
        try:
            # Prepare the request
            url = f"{self.session.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            # Prepare headers
            request_headers = self._prepare_headers(headers)
            
            # Prepare data
            request_data = self._prepare_data(data)

            # Create client session with retry logic
            async with aiohttp.ClientSession(
                timeout=self.client_timeout,
                headers=request_headers
            ) as client:
                for attempt in range(self.max_retries + 1):
                    try:
                        # Make the request
                        async with client.request(
                            method=method,
                            url=url,
                            json=request_data,
                            ssl=self.verify_ssl
                        ) as response:
                            # Wait for the response body to be fully received
                            await response.read()
                            
                            # Check if we should retry
                            if response.status in [429, 500, 502, 503, 504] and attempt < self.max_retries:
                                delay = self.backoff_factor * (2 ** attempt)
                                await asyncio.sleep(delay)
                                continue
                            
                            return response
                            
                    except aiohttp.ClientError as err:
                        if attempt < self.max_retries:
                            delay = self.backoff_factor * (2 ** attempt)
                            await asyncio.sleep(delay)
                            continue
                        return self._raise_error(err)

                return self._raise_error(aiohttp.ClientError("Max retries exceeded"))

        except ValueError as err:
            return self._raise_error(err)
        except aiohttp.ClientError as err:
            return self._raise_error(err)

    def _prepare_headers(self, headers: Optional[str]) -> Dict[str, str]:
        """Prepare request headers."""
        request_headers = {}
        if self.session.token:
            request_headers['Authorization'] = f"Bearer {self.session.token}"
        if headers:
            try:
                request_headers.update(json.loads(headers))
            except json.JSONDecodeError:
                raise ValueError("Headers must be in valid JSON format")
        return request_headers

    def _prepare_data(self, data: Optional[str]) -> Optional[Dict[str, Any]]:
        """Prepare request data."""
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise ValueError("Data must be in valid JSON format") 