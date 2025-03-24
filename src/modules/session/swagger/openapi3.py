"""OpenAPI 3.0 client implementation."""

import json
from typing import Dict, List, Optional, Any, Tuple, cast

from ...swagger.schema import SwaggerSpec, SwaggerSpecType, SwaggerEndpoint
from .base import SwaggerClient


class OpenAPI3Client(SwaggerClient):
    """Client for OpenAPI 3.0 specifications."""
    
    def __init__(self, swagger_spec: SwaggerSpec):
        """
        Initialize the OpenAPI 3.0 client.
        
        Args:
            swagger_spec: Parsed OpenAPI specification
        """
        if swagger_spec.spec_type != SwaggerSpecType.OPENAPI_3:
            raise ValueError(f"Expected OpenAPI 3.0 spec, got {swagger_spec.spec_type}")
        
        self._spec = swagger_spec
        
    @property
    def api_title(self) -> str:
        """Get the API title."""
        return self._spec.title
        
    @property
    def api_version(self) -> str:
        """Get the API version."""
        return self._spec.version
        
    @property
    def api_description(self) -> Optional[str]:
        """Get the API description."""
        return self._spec.description
        
    def get_available_endpoints(self, method: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get a list of available endpoints."""
        result = []
        
        for endpoint in self._spec.endpoints:
            # Filter by method if specified
            if method and endpoint.method.upper() != method.upper():
                continue
                
            result.append({
                'path': endpoint.path,
                'method': endpoint.method.upper(),
                'summary': endpoint.summary,
                'description': endpoint.description,
                'operation_id': endpoint.operation_id
            })
            
        return result
    
    def get_endpoint_details(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific endpoint."""
        for endpoint in self._spec.endpoints:
            if endpoint.path == path and endpoint.method.upper() == method.upper():
                return {
                    'path': endpoint.path,
                    'method': endpoint.method.upper(),
                    'summary': endpoint.summary,
                    'description': endpoint.description,
                    'operation_id': endpoint.operation_id,
                    'parameters': [
                        {
                            'name': param.name,
                            'in': param.in_location,
                            'required': param.required,
                            'type': param.type,
                            'description': param.description
                        }
                        for param in endpoint.parameters
                    ],
                    'request_body': endpoint.request_body,
                    'responses': endpoint.responses,
                    'tags': endpoint.tags
                }
                
        return None
        
    def get_request_sample(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Generate a sample request body for the specified endpoint."""
        for endpoint in self._spec.endpoints:
            if endpoint.path == path and endpoint.method.upper() == method.upper():
                if endpoint.request_body:
                    content = endpoint.request_body.get('content', {})
                    for content_type, content_obj in content.items():
                        if 'application/json' in content_type:
                            schema = content_obj.get('schema', {})
                            if schema:
                                return self._generate_sample_from_schema(schema)
                        
        return None
        
    def get_response_sample(self, path: str, method: str, status_code: str = "200") -> Optional[Dict[str, Any]]:
        """Generate a sample response for the specified endpoint."""
        for endpoint in self._spec.endpoints:
            if endpoint.path == path and endpoint.method.upper() == method.upper():
                response = endpoint.responses.get(status_code, {})
                content = response.get('content', {})
                for content_type, content_obj in content.items():
                    if 'application/json' in content_type:
                        schema = content_obj.get('schema', {})
                        if schema:
                            return self._generate_sample_from_schema(schema)
                        
        return None
        
    def get_header_samples(self, path: str, method: str) -> Dict[str, str]:
        """Get sample headers for the specified endpoint."""
        headers = {}
        
        for endpoint in self._spec.endpoints:
            if endpoint.path == path and endpoint.method.upper() == method.upper():
                # Check header parameters
                header_params = [p for p in endpoint.parameters if p.in_location == 'header']
                
                for param in header_params:
                    sample_value = "sample_value"
                    if param.enum and param.enum[0]:
                        sample_value = param.enum[0]
                    elif param.default is not None:
                        sample_value = str(param.default)
                        
                    headers[param.name] = sample_value
                    
                # Also check response headers for this endpoint
                for status, response in endpoint.responses.items():
                    resp_headers = response.get('headers', {})
                    for header_name, header_obj in resp_headers.items():
                        headers[header_name] = "response_value"
                
        return headers
        
    def validate_request(
        self, 
        path: str, 
        method: str, 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, List[str]]:
        """Validate a request against the schema."""
        # This is a simple implementation - a real one would use a JSON Schema validator
        errors = []
        
        # Find the endpoint
        endpoint_match = None
        for endpoint in self._spec.endpoints:
            if endpoint.path == path and endpoint.method.upper() == method.upper():
                endpoint_match = endpoint
                break
                
        if not endpoint_match:
            return False, ["Endpoint not found in specification"]
            
        # Check required parameters
        if headers:
            header_params = [p for p in endpoint_match.parameters if p.in_location == 'header']
            for param in header_params:
                if param.required and param.name not in headers:
                    errors.append(f"Missing required header parameter: {param.name}")
        
        # Check request body (very simple validation)
        if data and endpoint_match.request_body:
            # Check if request body is required
            if endpoint_match.request_body.get('required', False) and not data:
                errors.append("Request body is required but not provided")
                
            # Real validation would check against the schema
            # For the OpenAPI 3.0 spec, the request body has content with media types
                
        return len(errors) == 0, errors
    
    def _generate_sample_from_schema(self, schema: Dict[str, Any]) -> Any:
        """
        Generate a sample object from a JSON Schema.
        
        Args:
            schema: JSON Schema
            
        Returns:
            Sample data based on the schema
        """
        # Handle $ref (simple implementation - would need to be expanded)
        if '$ref' in schema:
            ref_path = schema['$ref']
            if ref_path.startswith('#/components/schemas/'):
                schema_name = ref_path.split('/')[-1]
                schema_def = self._spec.components.get('schemas', {}).get(schema_name, {})
                return self._generate_sample_from_schema(schema_def)
            return {}
            
        # Handle array
        if schema.get('type') == 'array' and 'items' in schema:
            items_schema = schema['items']
            return [self._generate_sample_from_schema(items_schema)]
            
        # Handle object
        if schema.get('type') == 'object' or 'properties' in schema:
            result = {}
            properties = schema.get('properties', {})
            
            for prop_name, prop_schema in properties.items():
                result[prop_name] = self._generate_value_for_property(prop_schema)
                
            return result
            
        # Handle primitives
        if schema.get('type') == 'string':
            if 'enum' in schema and schema['enum']:
                return schema['enum'][0]
            elif schema.get('format') == 'date-time':
                return "2023-01-01T00:00:00Z"
            elif schema.get('format') == 'date':
                return "2023-01-01"
            return "string"
        elif schema.get('type') == 'number' or schema.get('type') == 'integer':
            return 0
        elif schema.get('type') == 'boolean':
            return False
        
        # Default
        return {}
    
    def _generate_value_for_property(self, prop_schema: Dict[str, Any]) -> Any:
        """Generate a sample value for a property."""
        # Delegate to _generate_sample_from_schema
        return self._generate_sample_from_schema(prop_schema) 