from typing import Dict, Any, Optional
import aiohttp
from ..session.session import Session
from ..logging import BaseLogger


class RequestExecutor:
    """Executes HTTP requests with session authentication."""
    
    def __init__(self, session: Session, logger: BaseLogger):
        self.session = session
        self.logger = logger

    async def execute_request(self, method: str, path: str, headers: Optional[Dict[str, str]] = None, 
                            body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute an HTTP request with authentication."""
        url = f"{self.session.base_url.rstrip('/')}/{path.lstrip('/')}"
        
        # Get authentication headers
        auth_headers = self.session.get_headers()
        
        # Merge request headers with auth headers
        request_headers = {**auth_headers, **(headers or {})}
        
        async with aiohttp.ClientSession() as client:
            try:
                async with client.request(method, url, headers=request_headers, json=body) as response:
                    response_data = await response.json()
                    status = response.status
                    response_headers = dict(response.headers)

                    # Log response details
                    self.logger.log_status(status)
                    self.logger.log_headers(response_headers)
                    self.logger.log_body(response_data)

                    # If authentication failed, try to refresh and retry once
                    if status == 401 and self.session.authenticator:
                        self.logger.log_info("Authentication failed, attempting to refresh...")
                        await self.session.refresh_auth()
                        auth_headers = self.session.get_headers()
                        request_headers = {**auth_headers, **(headers or {})}
                        
                        async with client.request(method, url, headers=request_headers, json=body) as retry_response:
                            response_data = await retry_response.json()
                            status = retry_response.status
                            response_headers = dict(retry_response.headers)

                            self.logger.log_status(status)
                            self.logger.log_headers(response_headers)
                            self.logger.log_body(response_data)

                    return {
                        'status': status,
                        'headers': response_headers,
                        'body': response_data
                    }

            except aiohttp.ClientError as e:
                self.logger.log_error(f"Request failed: {str(e)}")
                raise 