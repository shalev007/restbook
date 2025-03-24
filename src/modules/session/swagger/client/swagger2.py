"""Swagger 2.0 client implementation."""

import json
from typing import Dict, List, Optional, Any, Tuple, cast

from ..schema import SwaggerSpec, SwaggerSpecType, SwaggerEndpoint
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
        # Find matching endpoint
        endpoint_match = None
        path_params = {}
        
        for endpoint in self._spec.endpoints:
            if endpoint.method.upper() == method.upper():
                is_match, params = self._match_path_with_params(endpoint.path, path)
                if is_match:
                    endpoint_match = endpoint
                    path_params = params
                    break
                
        if not endpoint_match:
            return None
            
        return {
            'path': endpoint_match.path,
            'method': endpoint_match.method.upper(),
            'summary': endpoint_match.summary,
            'description': endpoint_match.description,
            'operation_id': endpoint_match.operation_id,
            'parameters': [
                {
                    'name': param.name,
                    'in': param.in_location,
                    'required': param.required,
                    'type': param.type,
                    'description': param.description
                }
                for param in endpoint_match.parameters
            ],
            'responses': endpoint_match.responses,
            'tags': endpoint_match.tags,
            'path_params': path_params
        }
        
    def get_request_sample(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Generate a sample request body for the specified endpoint."""
        # Find matching endpoint
        endpoint_match = None
        path_params = {}
        
        for endpoint in self._spec.endpoints:
            if endpoint.method.upper() == method.upper():
                is_match, params = self._match_path_with_params(endpoint.path, path)
                if is_match:
                    endpoint_match = endpoint
                    path_params = params
                    break
                
        if not endpoint_match:
            return None
            
        # Generate sample data
        sample_data = {}
        
        # Add request body if present
        if endpoint_match.request_body:
            schema = endpoint_match.request_body.get('schema', {})
            if schema:
                body_sample = self._generate_sample_from_schema(schema)
                if body_sample:
                    sample_data = body_sample
                
        # Add body parameters if present
        body_params = [p for p in endpoint_match.parameters if p.in_location == 'body']
        if body_params:
            param_schema = body_params[0].param_schema
            if param_schema:
                body_sample = self._generate_sample_from_schema(param_schema)
                if body_sample:
                    sample_data = body_sample
                
        return sample_data if sample_data else None
        
    def get_response_sample(self, path: str, method: str, status_code: str = "200") -> Optional[Dict[str, Any]]:
        """Generate a sample response for the specified endpoint."""
        # Find matching endpoint
        endpoint_match = None
        
        for endpoint in self._spec.endpoints:
            if endpoint.method.upper() == method.upper():
                is_match, _ = self._match_path_with_params(endpoint.path, path)
                if is_match:
                    endpoint_match = endpoint
                    break
                
        if not endpoint_match:
            return None
            
        response = endpoint_match.responses.get(status_code, {})
        schema = response.get('schema', {})
        if schema:
            return self._generate_sample_from_schema(schema)
                    
        return None
        
    def get_header_samples(self, path: str, method: str) -> Dict[str, str]:
        """Get sample headers for the specified endpoint."""
        headers: Dict[str, str] = {}
        
        # Find matching endpoint
        endpoint_match = None
        
        for endpoint in self._spec.endpoints:
            if endpoint.method.upper() == method.upper():
                is_match, _ = self._match_path_with_params(endpoint.path, path)
                if is_match:
                    endpoint_match = endpoint
                    break
                
        if not endpoint_match:
            return headers
            
        header_params = [p for p in endpoint_match.parameters if p.in_location == 'header']
        
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
        errors = []
        
        # Find matching endpoint
        endpoint_match = None
        path_params = {}
        
        for endpoint in self._spec.endpoints:
            if endpoint.method.upper() == method.upper():
                is_match, params = self._match_path_with_params(endpoint.path, path)
                if is_match:
                    endpoint_match = endpoint
                    path_params = params
                    break
                
        if not endpoint_match:
            return False, ["Endpoint not found in specification"]
            
        # Validate path parameters
        path_param_names = self._get_path_params(endpoint_match.path)
        for param_name in path_param_names:
            if param_name not in path_params:
                errors.append(f"Missing required path parameter: {param_name}")
            else:
                # Find the parameter definition
                param = next((p for p in endpoint_match.parameters if p.name == param_name and p.in_location == 'path'), None)
                if param:
                    # Validate the parameter value
                    if param.enum and path_params[param_name] not in param.enum:
                        errors.append(f"Invalid value for path parameter {param_name}: must be one of {param.enum}")
            
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
            
    def _generate_sample_value(self, param: Any) -> Any:
        """Generate a sample value for a parameter."""
        if param.enum and param.enum[0]:
            return param.enum[0]
        elif param.default is not None:
            return param.default
        elif param.type == 'string':
            return "string"
        elif param.type == 'integer' or param.type == 'number':
            return 0
        elif param.type == 'boolean':
            return False
        else:
            return None 