"""Parser for Swagger/OpenAPI specifications."""

import os
import json
import yaml
import requests
import uuid
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urlparse

from .schema import (
    SwaggerSpec, 
    SwaggerEndpoint, 
    SwaggerEndpointParameter, 
    SwaggerSpecType
)


class SwaggerParserError(Exception):
    """Error raised during Swagger parsing."""
    pass


class SwaggerParser:
    """Parser for Swagger/OpenAPI specifications."""

    def __init__(self):
        """Initialize the parser."""
        self.cache: Dict[str, SwaggerSpec] = {}

    def parse(self, source: str) -> SwaggerSpec:
        """
        Parse a Swagger/OpenAPI specification.
        
        Args:
            source: Path to a local file or URL to a remote specification
            
        Returns:
            SwaggerSpec: Parsed Swagger specification
            
        Raises:
            SwaggerParserError: If parsing fails
        """
        # Check if the source is already in the cache
        if source in self.cache:
            return self.cache[source]
            
        # Load the specification
        try:
            spec_data = self._load_spec(source)
        except Exception as e:
            raise SwaggerParserError(f"Failed to load Swagger spec from {source}: {str(e)}")

        # Parse the specification
        try:
            swagger_spec = self._parse_spec(spec_data, source)
            self.cache[source] = swagger_spec
            return swagger_spec
        except Exception as e:
            raise SwaggerParserError(f"Failed to parse Swagger spec: {str(e)}")

    def _load_spec(self, source: str) -> Dict[str, Any]:
        """
        Load a Swagger specification from a file or URL.
        
        Args:
            source: Path to a local file or URL to a remote specification
            
        Returns:
            Dict[str, Any]: Loaded specification data
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the source format is invalid
        """
        # Check if source is a URL
        parsed_url = urlparse(source)
        if parsed_url.scheme in ('http', 'https'):
            # Load from URL
            response = requests.get(source)
            response.raise_for_status()
            content = response.text
            
            # Determine format (JSON or YAML)
            if response.headers.get('Content-Type', '').startswith('application/json'):
                return json.loads(content)
            else:
                return yaml.safe_load(content)
        
        # Load from file
        if not os.path.exists(source):
            raise FileNotFoundError(f"Swagger spec file not found: {source}")
            
        with open(source, 'r') as f:
            content = f.read()
            
        # Try to parse as JSON, fall back to YAML
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid Swagger spec format: {str(e)}")

    def _parse_spec(self, spec_data: Dict[str, Any], source: str) -> SwaggerSpec:
        """
        Parse a Swagger specification from raw data.
        
        Args:
            spec_data: Loaded specification data
            source: Original source of the specification
            
        Returns:
            SwaggerSpec: Parsed Swagger specification
            
        Raises:
            ValueError: If the specification is invalid
        """
        # Determine spec type
        spec_type = self._detect_spec_type(spec_data)
        
        # Extract basic info
        if spec_type == SwaggerSpecType.SWAGGER_2:
            info = spec_data.get('info', {})
            title = info.get('title', 'Unknown API')
            version = info.get('version', '1.0.0')
            description = info.get('description')
            base_path = spec_data.get('basePath', '')
            definitions = spec_data.get('definitions', {})
            components = {}
        else:  # OpenAPI 3
            info = spec_data.get('info', {})
            title = info.get('title', 'Unknown API')
            version = info.get('version', '1.0.0')
            description = info.get('description')
            base_path = spec_data.get('servers', [{}])[0].get('url', '')
            definitions = {}
            components = spec_data.get('components', {})
        
        # Parse endpoints
        paths_data = spec_data.get('paths', {})
        endpoints = self._parse_endpoints(paths_data, spec_type)
        
        # Create the spec object
        is_url = urlparse(source).scheme in ('http', 'https')
        swagger_spec = SwaggerSpec(
            title=title,
            version=version,
            description=description,
            spec_type=SwaggerSpecType(spec_type),
            endpoints=endpoints,
            paths=paths_data,
            definitions=definitions,
            components=components,
            base_path=base_path,
            swagger_url=source if is_url else None,
            swagger_source=None if is_url else source
        )
        
        return swagger_spec

    def _detect_spec_type(self, spec_data: Dict[str, Any]) -> SwaggerSpecType:
        """
        Detect the type of Swagger/OpenAPI specification.
        
        Args:
            spec_data: Loaded specification data
            
        Returns:
            SwaggerSpecType: Detected specification type
            
        Raises:
            ValueError: If the specification type cannot be determined
        """
        if 'swagger' in spec_data:
            version = spec_data['swagger']
            if version.startswith('2.'):
                return SwaggerSpecType.SWAGGER_2
        elif 'openapi' in spec_data:
            version = spec_data['openapi']
            if version.startswith('3.'):
                return SwaggerSpecType.OPENAPI_3
                
        raise ValueError(f"Unknown Swagger/OpenAPI specification version")

    def _parse_endpoints(
        self, 
        paths_data: Dict[str, Dict[str, Any]],
        spec_type: SwaggerSpecType
    ) -> List[SwaggerEndpoint]:
        """
        Parse endpoints from a Swagger specification.
        
        Args:
            paths_data: Paths data from the specification
            spec_type: Detected specification type
            
        Returns:
            List[SwaggerEndpoint]: Parsed endpoints
        """
        endpoints = []
        
        for path, path_item in paths_data.items():
            for method, operation in path_item.items():
                # Skip non-operation keys
                if method in ('parameters', '$ref'):
                    continue
                    
                # Extract operation info
                operation_id = operation.get('operationId')
                summary = operation.get('summary')
                description = operation.get('description')
                tags = operation.get('tags', [])
                
                # Parse parameters
                parameters = self._parse_parameters(operation, path_item, spec_type)
                
                # Handle request body differently based on spec version
                request_body = None
                if spec_type == SwaggerSpecType.SWAGGER_2:
                    # In Swagger 2.0, the request body is defined in parameters with "in: body"
                    body_params = [p for p in parameters if p.in_location == 'body']
                    if body_params:
                        # Access the actual field directly to avoid the property method
                        request_body = {'schema': body_params[0].param_schema}
                else:
                    # In OpenAPI 3.0, the request body is defined separately
                    request_body = operation.get('requestBody')
                
                # Create endpoint
                endpoint = SwaggerEndpoint(
                    path=path,
                    method=method,
                    operation_id=operation_id,
                    summary=summary,
                    description=description,
                    parameters=parameters,
                    request_body=request_body,
                    responses=operation.get('responses', {}),
                    tags=tags
                )
                
                endpoints.append(endpoint)
                
        return endpoints

    def _parse_parameters(
        self,
        operation: Dict[str, Any],
        path_item: Dict[str, Any],
        spec_type: SwaggerSpecType
    ) -> List[SwaggerEndpointParameter]:
        """
        Parse parameters from an operation.
        
        Args:
            operation: Operation data
            path_item: Path item data
            spec_type: Detected specification type
            
        Returns:
            List[SwaggerEndpointParameter]: Parsed parameters
        """
        # Combine path-level and operation-level parameters
        params_data = []
        
        # Add path-level parameters
        path_params = path_item.get('parameters', [])
        params_data.extend(path_params)
        
        # Add operation-level parameters
        op_params = operation.get('parameters', [])
        params_data.extend(op_params)
        
        # Parse parameters
        parameters = []
        for param_data in params_data:
            # Handle $ref
            if '$ref' in param_data:
                # In a real implementation, resolve the reference
                # For now, we'll just skip it
                continue
                
            # Extract parameter info
            param_name = param_data.get('name', '')
            param_in = param_data.get('in', '')
            param_desc = param_data.get('description')
            param_required = param_data.get('required', False)
            
            # Handle different spec versions
            if spec_type == SwaggerSpecType.SWAGGER_2:
                param_type = param_data.get('type')
                param_format = param_data.get('format')
                param_enum = param_data.get('enum')
                param_default = param_data.get('default')
                param_schema = param_data.get('schema')
            else:
                # In OpenAPI 3.0, most properties are in the schema object
                schema = param_data.get('schema', {})
                param_type = schema.get('type')
                param_format = schema.get('format')
                param_enum = schema.get('enum')
                param_default = schema.get('default')
                param_schema = schema
            
            # Create parameter
            parameter = SwaggerEndpointParameter(
                name=param_name,
                **{"in": param_in},
                description=param_desc,
                required=param_required,
                type=param_type,
                format=param_format,
                enum=param_enum,
                default=param_default,
                schema=param_schema
            )
            
            parameters.append(parameter)
            
        return parameters
        
    def save_swagger_spec(self, spec: SwaggerSpec, name: str) -> str:
        """
        Save Swagger spec to a file and return its path.
        
        Args:
            spec: The SwaggerSpec to save
            name: Name to use in the filename
            
        Returns:
            str: Path to the saved spec file
        """
        swagger_dir = Path.home() / '.restbook' / 'swagger'
        swagger_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename using session name and uuid
        filename = f"{name}-{uuid.uuid4()}.json"
        filepath = swagger_dir / filename
        
        # Save spec as JSON using Pydantic's built-in JSON serialization
        with open(filepath, 'w') as f:
            f.write(spec.model_dump_json(indent=2, by_alias=True))
            
        return str(filepath) 