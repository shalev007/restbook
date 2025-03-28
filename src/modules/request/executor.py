import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, NoReturn, List
from aiohttp import ClientTimeout
from pydantic import BaseModel

from .aio_client_cache import AioSessionCache
from .circuit_breaker import CircuitBreaker
from .errors import AuthenticationError, RetryExceededError, RetryableError, SSLVerificationError, UnknownError
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
        circuit_breaker: Optional[CircuitBreaker] = None,
        session_cache: Optional[AioSessionCache] = None,
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
        self.circuit_breaker = circuit_breaker  # Allow it to be None
        self.session_cache = session_cache or AioSessionCache()
        

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
                    # Only check circuit breaker if it exists
                    if self.circuit_breaker and self.circuit_breaker.is_open():
                        self.logger.log_error(f"Circuit breaker is open, waiting {self.config.circuit_breaker_reset} seconds before next attempt...")
                        await asyncio.sleep(self.config.circuit_breaker_reset)
                    
                    params = await self._build_request_params(request_params)
                    # Get fresh headers for each attempt in case of auth refresh
                    # Make the request
                    response = await client.request(
                        method=params["method"],
                        url=params["url"],
                        json=params["data"],
                        params=params["params"],
                        headers=params["headers"],
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
                    
                    # Only record success if circuit breaker exists
                    if self.circuit_breaker:
                        self.circuit_breaker.record_success()
                    return response
                except AuthenticationError:
                    if attempt < self.config.max_retries:
                        if await self._handle_auth_retry():
                            continue
                        raise AuthenticationError("Authentication failed after retries")
                except RetryableError:
                    if attempt < self.config.max_retries:
                        # Only record failure if circuit breaker exists
                        if self.circuit_breaker:
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
                        # Only record failure if circuit breaker exists
                        if self.circuit_breaker:
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
                except Exception as err:
                    self.logger.log_error(f"Unexpected error: {str(err)}")
                    raise UnknownError(f"Unexpected error: {str(err)}")

            raise UnknownError("Request failed in an unexpected way - reached end of retry loop without success or specific error")
        finally:
            # Always close the session after execution
            await self.session_cache.close()

    async def _build_request_params(self, request_params: RequestParams) -> Dict[str, Any]:
        """Build the request parameters for the request.
        
        Args:
            request_params: Configuration for the request to execute
        """

        request_headers = {}
        if not self.session.is_authenticated():
            await self.session.authenticate()
        request_headers = self.session.get_headers()
        if request_params.headers:
            request_headers.update(request_params.headers)

        return {
            "url": f"{self.session.base_url.rstrip('/')}/{request_params.url.lstrip('/')}",
            "method": request_params.method,
            "headers": request_headers,
            "data": request_params.data,
            "params": request_params.params
        }

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

    async def close(self):
        """Close the client session cache."""
        await self.session_cache.close() 