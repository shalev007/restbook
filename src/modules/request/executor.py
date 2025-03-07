import json
import requests
from typing import Optional, Dict, Any
from ..logging import BaseLogger
from ..session.session_store import SessionStore


class RequestExecutor:
    """Handles HTTP request execution and response processing."""
    
    def __init__(self, session_store: SessionStore, logger: BaseLogger):
        self.session_store = session_store
        self.logger = logger

    def execute_request(
        self,
        session_name: str,
        method: str,
        endpoint: str,
        data: Optional[str] = None,
        headers: Optional[str] = None
    ) -> None:
        """Execute an HTTP request using the specified session.
        
        Args:
            session_name: Name of the session to use
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Optional JSON data to send with the request
            headers: Optional JSON string of additional headers
        """
        try:
            # Get the session
            sessions = self.session_store.list_sessions()
            if session_name not in sessions:
                error_msg = f"Session '{session_name}' does not exist."
                self.logger.log_error(error_msg)
                raise ValueError(error_msg)
            session = sessions[session_name]

            # Prepare the request
            url = f"{session.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            # Prepare headers
            request_headers = self._prepare_headers(session.token, headers)
            
            # Prepare data
            request_data = self._prepare_data(data)

            # Make the request
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                json=request_data
            )

            # Log response
            self._log_response(response)

        except ValueError as err:
            self.logger.log_error(str(err))
        except requests.exceptions.RequestException as err:
            self.logger.log_error(f"Request failed: {str(err)}")

    def _prepare_headers(self, token: Optional[str], headers: Optional[str]) -> Dict[str, str]:
        """Prepare request headers."""
        request_headers = {}
        if token:
            request_headers['Authorization'] = f"Bearer {token}"
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