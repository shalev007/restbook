"""Base class for Swagger client functionality."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import re

class SwaggerClient(ABC):
    """
    Abstract base class for Swagger clients.
    
    This class defines the interface for interacting with Swagger/OpenAPI specifications
    regardless of the specific version. Implementations for different versions (2.0, 3.0)
    should inherit from this class and implement its methods.
    """
    
    @property
    @abstractmethod
    def api_title(self) -> str:
        """Get the API title."""
        pass
        
    @property
    @abstractmethod
    def api_version(self) -> str:
        """Get the API version."""
        pass
        
    @property
    @abstractmethod
    def api_description(self) -> Optional[str]:
        """Get the API description."""
        pass
        
    @abstractmethod
    def get_available_endpoints(self, method: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get a list of available endpoints.
        
        Args:
            method: Optional HTTP method to filter by (GET, POST, etc.)
            
        Returns:
            List of endpoint dictionaries with keys:
            - path: The endpoint path
            - method: The HTTP method
            - summary: Short description (if available)
            - description: Longer description (if available)
            - operation_id: Unique identifier for the operation
        """
        pass
    
    @abstractmethod
    def get_endpoint_details(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific endpoint.
        
        Args:
            path: The endpoint path
            method: The HTTP method
            
        Returns:
            Dictionary with endpoint details or None if not found.
        """
        pass
        
    @abstractmethod
    def get_request_sample(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """
        Generate a sample request body for the specified endpoint.
        
        Args:
            path: The endpoint path
            method: The HTTP method
            
        Returns:
            Sample request data or None if not applicable.
        """
        pass
        
    @abstractmethod
    def get_response_sample(self, path: str, method: str, status_code: str = "200") -> Optional[Dict[str, Any]]:
        """
        Generate a sample response for the specified endpoint.
        
        Args:
            path: The endpoint path
            method: The HTTP method
            status_code: The HTTP status code
            
        Returns:
            Sample response data or None if not available.
        """
        pass
        
    @abstractmethod
    def get_header_samples(self, path: str, method: str) -> Dict[str, str]:
        """
        Get sample headers for the specified endpoint.
        
        Args:
            path: The endpoint path
            method: The HTTP method
            
        Returns:
            Dictionary of header name to sample value.
        """
        pass
        
    @abstractmethod
    def validate_request(
        self, 
        path: str, 
        method: str, 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate a request against the schema.
        
        Args:
            path: The endpoint path
            method: The HTTP method
            data: Request data
            headers: Request headers
            
        Returns:
            Tuple of (is_valid, error_messages).
        """
        pass

    def _match_path_with_params(self, spec_path: str, request_path: str) -> Tuple[bool, Dict[str, str]]:
        """
        Match a request path against a spec path with parameters.
        
        Args:
            spec_path: Path from the specification (e.g. /pet/{petId})
            request_path: Actual request path (e.g. /pet/123)
            
        Returns:
            Tuple of (is_match, path_params) where path_params is a dict of parameter name to value
        """
        # Convert spec path to regex pattern
        pattern = spec_path.replace('{', '(?P<').replace('}', '>[^/]+)')
        match = re.match(f'^{pattern}$', request_path)
        
        if not match:
            return False, {}
            
        return True, match.groupdict()
        
    def _get_path_params(self, spec_path: str) -> List[str]:
        """
        Extract path parameters from a spec path.
        
        Args:
            spec_path: Path from the specification (e.g. /pet/{petId})
            
        Returns:
            List of parameter names
        """
        return re.findall(r'{([^}]+)}', spec_path)
        
    def _replace_path_params(self, spec_path: str, params: Dict[str, str]) -> str:
        """
        Replace path parameters in a spec path with their values.
        
        Args:
            spec_path: Path from the specification (e.g. /pet/{petId})
            params: Dictionary of parameter name to value
            
        Returns:
            Path with parameters replaced
        """
        result = spec_path
        for name, value in params.items():
            result = result.replace(f'{{{name}}}', value)
        return result 