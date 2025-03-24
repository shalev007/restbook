"""Factory for creating Swagger clients."""

from typing import Optional
import os
import json
import logging

from ..schema import SwaggerSpec, SwaggerSpecType, SwaggerEndpoint, SwaggerEndpointParameter
from ..parser import SwaggerParser, SwaggerParserError

from .base import SwaggerClient
from .swagger2 import Swagger2Client
from .openapi3 import OpenAPI3Client


class SwaggerClientFactory:
    """Factory for creating Swagger clients."""
    
    @staticmethod
    def create_from_file(file_path: str) -> Optional[SwaggerClient]:
        """
        Create a Swagger client from a specification file.
        
        Args:
            file_path: Path to the Swagger/OpenAPI specification file
            
        Returns:
            SwaggerClient: Appropriate client for the specification version
        """
        if not os.path.exists(file_path):
            return None
        
        logging.debug(f"Creating Swagger client from file: {file_path}")
            
        try:
            # First try to load as a serialized SwaggerSpec JSON file
            with open(file_path, 'r') as f:
                spec_data = json.load(f)
                
            # Check if this looks like a serialized SwaggerSpec
            if all(key in spec_data for key in ('spec_type', 'title', 'version')):
                # It's likely a serialized SwaggerSpec
                logging.debug("File appears to be a serialized SwaggerSpec, attempting to load")
                try:
                    # Use model_validate (Pydantic v2)
                    swagger_spec = SwaggerSpec.model_validate(spec_data)
                    logging.debug(f"Successfully loaded serialized SwaggerSpec: {swagger_spec.title} v{swagger_spec.version}")
                    return SwaggerClientFactory.create_from_spec(swagger_spec)
                except Exception as e:
                    logging.warning(f"Error deserializing SwaggerSpec: {e}")
                    
                    # Alternative approach: try manual reconstruction
                    try:
                        logging.debug("Attempting manual reconstruction of SwaggerSpec")
                        # Manual reconstruction of the object
                        if isinstance(spec_data['spec_type'], str):
                            spec_data['spec_type'] = SwaggerSpecType(spec_data['spec_type'])
                            
                        # Create endpoints with proper model instances
                        endpoints = []
                        for ep_data in spec_data.get('endpoints', []):
                            # Create parameter objects
                            parameters = []
                            for param_data in ep_data.get('parameters', []):
                                parameters.append(SwaggerEndpointParameter(**param_data))
                                
                            # Create endpoint with parameters
                            ep_data['parameters'] = parameters
                            endpoints.append(SwaggerEndpoint(**ep_data))
                            
                        # Update spec data
                        spec_data['endpoints'] = endpoints
                        
                        # Create the spec
                        swagger_spec = SwaggerSpec(**spec_data)
                        logging.debug(f"Manual reconstruction successful: {swagger_spec.title} v{swagger_spec.version}")
                        return SwaggerClientFactory.create_from_spec(swagger_spec)
                    except Exception as e2:
                        logging.warning(f"Manual reconstruction failed: {e2}")
                        # Continue to try parsing as raw spec
            
            # If we get here, it's not a serialized SwaggerSpec or deserialization failed
            # Fall back to parsing as a raw Swagger/OpenAPI spec
            logging.debug("Attempting to parse file as raw Swagger/OpenAPI spec")
            parser = SwaggerParser()
            spec = parser.parse(file_path)
            logging.debug(f"Successfully parsed raw spec: {spec.title} v{spec.version}")
            return SwaggerClientFactory.create_from_spec(spec)
            
        except SwaggerParserError as e:
            logging.error(f"Error parsing Swagger specification: {e}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in file: {e}")
            return None
        except Exception as e:
            logging.error(f"Error creating Swagger client: {e}")
            return None
    
    @staticmethod
    def create_from_spec(spec: SwaggerSpec) -> Optional[SwaggerClient]:
        """
        Create a Swagger client from a parsed specification.
        
        Args:
            spec: Parsed Swagger/OpenAPI specification
            
        Returns:
            SwaggerClient: Appropriate client for the specification version
        """
        try:
            client: Optional[SwaggerClient] = None
            
            if spec.spec_type == SwaggerSpecType.SWAGGER_2:
                client = Swagger2Client(spec)
                logging.debug(f"Created Swagger 2.0 client for {spec.title}")
            elif spec.spec_type == SwaggerSpecType.OPENAPI_3:
                client = OpenAPI3Client(spec)
                logging.debug(f"Created OpenAPI 3.0 client for {spec.title}")
            else:
                logging.warning(f"Unsupported spec type: {spec.spec_type}")
                return None
                
            return client
        except Exception as e:
            logging.error(f"Error creating client from spec: {e}")
            return None 