import json
import requests
from typing import Optional, Dict, Any
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from src.modules.session.session import Session
from ..logging import BaseLogger


class RequestExecutor:
    """Handles HTTP request execution and response processing."""
    
    def __init__(
        self,
        base_url: str,
        session: Session,
        logger: BaseLogger,
        timeout: int = 30,
        verify_ssl: bool = True,
        max_retries: int = 3,
        backoff_factor: float = 0.5
    ):
        self.base_url = base_url
        self.auth_session = session
        self.logger = logger
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    async def execute_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[str] = None,
        headers: Optional[str] = None
    ) -> None:
        """Execute an HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Optional JSON data to send with the request
            headers: Optional JSON string of additional headers
        """
        try:
            # Prepare the request
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            # Prepare headers
            request_headers = self._prepare_headers(headers)
            
            # Prepare data
            request_data = self._prepare_data(data)

            # Make the request
            response = self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                json=request_data,
                timeout=self.timeout,
                verify=self.verify_ssl
            )

            # Log response
            self._log_response(response)

        except ValueError as err:
            self.logger.log_error(str(err))
        except requests.exceptions.RequestException as err:
            self.logger.log_error(f"Request failed: {str(err)}")

    def _prepare_headers(self, headers: Optional[str]) -> Dict[str, str]:
        """Prepare request headers."""
        request_headers = {}
        if self.auth_session.token:
            request_headers['Authorization'] = f"Bearer {self.auth_session.token}"
        if headers:
            try:
                request_headers.update(json.loads(headers))
            except json.JSONDecodeError:
                error_msg = "Headers must be in valid JSON format"
                self.logger.log_error(error_msg)
                raise ValueError(error_msg)
        return request_headers

    def _prepare_data(self, data: Optional[str]) -> Optional[Dict[str, Any]]:
        """Prepare request data."""
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            error_msg = "Data must be in valid JSON format"
            self.logger.log_error(error_msg)
            raise ValueError(error_msg)

    def _log_response(self, response: requests.Response) -> None:
        """Log the response details."""
        self.logger.log_status(response.status_code)
        self.logger.log_headers(dict(response.headers))
        try:
            body = json.dumps(response.json(), indent=2)
        except:
            body = response.text
        self.logger.log_body(body) 