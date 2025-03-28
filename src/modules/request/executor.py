import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, NoReturn, List
from aiohttp import ClientTimeout
from pydantic import BaseModel

from .aio_client_cache import AioSessionCache
from .circuit_breaker import CircuitBreaker
from .errors import AuthenticationError, JSONError, RetryExceededError, RetryableError, SSLVerificationError, UnknownError
from ..logging import BaseLogger
from ..session.session import Session

class ResilientHttpClientConfig(BaseModel):
    timeout: int = 30
    verify_ssl: bool = True
    max_retries: int = 3
    backoff_factor: float = 0.5
    circuit_breaker_threshold: int = 3   # number of failures before opening the circuit
    circuit_breaker_reset: int = 10      # seconds to wait before resetting circuit breaker

class RequestParams(BaseModel):
    url: str
    method: str
    headers: Optional[Dict[str, str]] = None
    data: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    

class ResilientHttpClient:
    """Handles HTTP request execution and response processing."""
    
    # Status codes that should trigger retries
    RETRY_STATUS_CODES: List[int] = [429, 500, 502, 503, 504]
    
    # Status codes that might indicate auth issues
    AUTH_STATUS_CODES: List[int] = [401, 403]
    
    def __init__(
        self,
        session: Session,
        config: ResilientHttpClientConfig,
        logger: BaseLogger,
        session_cache: Optional[AioSessionCache] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        """Initialize the request executor.
        
        Args:
            session: Session object containing base URL and authentication details
            config: Request execution configuration
            logger: Logger instance for logging requests and responses
            session_cache: Optional session cache for reusing HTTP sessions
            circuit_breaker: Optional circuit breaker for handling failures
        """
        self.session = session
        self.config = config
        self.logger = logger
        self.session_cache = session_cache or AioSessionCache()
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            threshold=config.circuit_breaker_threshold,
            reset_timeout=config.circuit_breaker_reset
        )
        

    async def execute_request(
        self,
        request_params: RequestParams
    ) -> aiohttp.ClientResponse:
        """Execute an HTTP request asynchronously.
        
        Args:
            request_params: Configuration for the request to execute
            
        Returns:
            aiohttp.ClientResponse: The response from the server
            
        Raises:
            AuthenticationError: If authentication fails
            RetryExceededError: If max retries are exceeded
            SSLVerificationError: If SSL verification fails
            UnknownError: If an unknown error occurs
            JSONError: If data is not valid JSON
        """

        # Get or create client session
        client = await self.session_cache.get_session(
            timeout=self.config.timeout,
        )

        try:
            for attempt in range(self.config.max_retries + 1):
                response = None
                try:
                    # Wait if circuit breaker is open instead of throwing an error
                    while self.circuit_breaker.is_open():
                        self.logger.log_error(f"Circuit breaker is open, waiting {self.config.circuit_breaker_reset} seconds before next attempt...")
                        await asyncio.sleep(self.config.circuit_breaker_reset)
                        
                    # Get fresh headers for each attempt in case of auth refresh
                    request_headers = await self._prepare_headers(request_params.headers)
                    
                    # Make the request
                    response = await client.request(
                        method=request_params.method,
                        url=self._build_url(request_params.url),
                        json=request_params.data,
                        params=request_params.params,
                        headers=request_headers,
                        ssl=self.config.verify_ssl
                    )
                    
                    # Wait for the response body to be fully received
                    await response.read()
                    
                    # Handle authentication errors
                    if response.status in self.AUTH_STATUS_CODES:
                        self.logger.log_error(f"Authentication failed with status code {response.status}")
                        raise AuthenticationError("Authentication failed")
                    
                    # Check if we should retry other errors
                    if response.status in self.RETRY_STATUS_CODES:
                        self.logger.log_error(f"Server returned a retryable status code {response.status}")
                        raise RetryableError("Server returned a retryable status code")
                    
                    # Record success and return response
                    self.circuit_breaker.record_success()
                    return response
                except AuthenticationError:
                    if attempt < self.config.max_retries:
                        if await self._handle_auth_retry():
                            continue
                        raise AuthenticationError("Authentication failed after retries")
                except RetryableError:
                    if attempt < self.config.max_retries:
                        self.circuit_breaker.record_failure()
                        await self._handle_retry_delay(attempt)
                        continue
                    raise RetryExceededError("Max retries exceeded")
                except aiohttp.ClientSSLError as err:
                    self.logger.log_error(f"SSL error: {str(err)}, check your SSL configuration or try setting verify_ssl to False")
                    # SSL errors are usually configuration issues, don't retry
                    raise SSLVerificationError(f"SSL verification failed: {str(err)}")
                except aiohttp.ClientConnectorError as err:
                    self.logger.log_error(f"Connection error: {str(err)}")
                    if attempt < self.config.max_retries:
                        self.circuit_breaker.record_failure()
                        await self._handle_retry_delay(attempt)
                        continue
                    raise RetryExceededError(f"Connection failed after {self.config.max_retries} attempts: {str(err)}")
                except aiohttp.InvalidURL as err:
                    # URL errors are configuration issues, don't retry
                    self.logger.log_error(f"Invalid URL: {str(err)}, check your URL configuration")
                    raise UnknownError(f"Invalid URL configuration: {str(err)}")
                except aiohttp.ClientError as err:
                    self.logger.log_error(f"Client error: {str(err)}")
                    if attempt < self.config.max_retries:
                        await self._handle_retry_delay(attempt)
                        continue
                    raise RetryExceededError(f"Request failed after {self.config.max_retries} attempts: {str(err)}")

            raise UnknownError("Request failed in an unexpected way - reached end of retry loop without success or specific error")
        finally:
            # Always close the session after execution
            await self.session_cache.close()

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
        delay = self.config.backoff_factor * (2 ** attempt)
        await asyncio.sleep(delay)

    def _prepare_data(self, data: Optional[str]) -> Optional[Dict[str, Any]]:
        """Prepare request data.
        
        Args:
            data: JSON string to convert to dictionary
            
        Returns:
            Optional[Dict[str, Any]]: Parsed JSON data as dictionary
            
        Raises:
            JSONError: If data is not valid JSON
        """
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise JSONError(f"Data must be in valid JSON format: {data}")

    async def close(self):
        """Close the client session cache."""
        await self.session_cache.close() 