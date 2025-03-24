"""Swagger 2.0 client implementation."""

import json
from typing import Dict, List, Optional, Any, Tuple, cast

from ...swagger.schema import SwaggerSpec, SwaggerSpecType, SwaggerEndpoint
from .base import SwaggerClient


class Swagger2Client(SwaggerClient):
    """Client for Swagger 2.0 specifications."""
    
    def __init__(self, swagger_spec: SwaggerSpec):
        """
        Initialize the Swagger 2.0 client.
        
        Args:
            swagger_spec: Parsed Swagger specification
        """
        if swagger_spec.spec_type != SwaggerSpecType.SWAGGER_2:
            raise ValueError(f"Expected Swagger 2.0 spec, got {swagger_spec.spec_type}")
        
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
                    'responses': endpoint.responses,
                    'tags': endpoint.tags
                }
                
        return None
        
    def get_request_sample(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Generate a sample request body for the specified endpoint."""
        for endpoint in self._spec.endpoints:
            if endpoint.path == path and endpoint.method.upper() == method.upper():
                if endpoint.request_body:
                    schema = endpoint.request_body.get('schema', {})
                    if schema:
                        return self._generate_sample_from_schema(schema)
                
                # If no request body but there are body parameters
                body_params = [p for p in endpoint.parameters if p.in_location == 'body']
                if body_params:
                    param_schema = body_params[0].param_schema
                    if param_schema:
                        return self._generate_sample_from_schema(param_schema)
                        
        return None
        
    def get_response_sample(self, path: str, method: str, status_code: str = "200") -> Optional[Dict[str, Any]]:
        """Generate a sample response for the specified endpoint."""
        for endpoint in self._spec.endpoints:
            if endpoint.path == path and endpoint.method.upper() == method.upper():
                response = endpoint.responses.get(status_code, {})
                schema = response.get('schema', {})
                if schema:
                    return self._generate_sample_from_schema(schema)
                        
        return None
        
    def get_header_samples(self, path: str, method: str) -> Dict[str, str]:
        """Get sample headers for the specified endpoint."""
        headers = {}
        
        for endpoint in self._spec.endpoints:
            if endpoint.path == path and endpoint.method.upper() == method.upper():
                header_params = [p for p in endpoint.parameters if p.in_location == 'header']
                
                for param in header_params:
                    sample_value = "sample_value"
                    if param.enum and param.enum[0]:
                        sample_value = param.enum[0]
                    elif param.default is not None:
                        sample_value = str(param.default)
                        
                    headers[param.name] = sample_value
                
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
        if data:
            body_params = [p for p in endpoint_match.parameters if p.in_location == 'body']
            if body_params and body_params[0].param_schema:
                # Real validation would check against the schema
                pass
                
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
            if ref_path.startswith('#/definitions/'):
                definition_name = ref_path.split('/')[-1]
                definition = self._spec.definitions.get(definition_name, {})
                return self._generate_sample_from_schema(definition)
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
            return "string"
        elif schema.get('type') == 'number' or schema.get('type') == 'integer':
            return 0
        elif schema.get('type') == 'boolean':
            return False
        
        # Default
        return {}
    
    def _generate_value_for_property(self, prop_schema: Dict[str, Any]) -> Any:
        """Generate a sample value for a property."""
        if '$ref' in prop_schema:
            ref_path = prop_schema['$ref']
            if ref_path.startswith('#/definitions/'):
                definition_name = ref_path.split('/')[-1]
                definition = self._spec.definitions.get(definition_name, {})
                return self._generate_sample_from_schema(definition)
            return {}
            
        prop_type = prop_schema.get('type', 'string')
        
        if prop_type == 'object':
            return self._generate_sample_from_schema(prop_schema)
        elif prop_type == 'array':
            items = prop_schema.get('items', {})
            return [self._generate_value_for_property(items)]
        elif prop_type == 'string':
            if 'enum' in prop_schema and prop_schema['enum']:
                return prop_schema['enum'][0]
            elif prop_schema.get('format') == 'date-time':
                return "2023-01-01T00:00:00Z"
            elif prop_schema.get('format') == 'date':
                return "2023-01-01"
            return "string"
        elif prop_type == 'integer' or prop_type == 'number':
            return 0
        elif prop_type == 'boolean':
            return False
        else:
            return None 