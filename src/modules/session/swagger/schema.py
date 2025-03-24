"""Data models for Swagger/OpenAPI specifications."""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class SwaggerSpecType(str, Enum):
    """Supported Swagger/OpenAPI specification types."""
    SWAGGER_2 = "swagger_2"
    OPENAPI_3 = "openapi_3"


class SwaggerEndpointParameter(BaseModel):
    """Parameter for a Swagger endpoint."""
    name: str
    in_location: str = Field(..., alias="in")
    description: Optional[str] = None
    required: bool = False
    type: Optional[str] = None
    param_schema: Optional[Dict[str, Any]] = Field(None, alias="schema")
    format: Optional[str] = None
    enum: Optional[List[str]] = None
    default: Optional[Any] = None
    

class SwaggerEndpoint(BaseModel):
    """Endpoint from a Swagger/OpenAPI specification."""
    path: str
    method: str
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[SwaggerEndpointParameter] = []
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = {}
    tags: List[str] = []


class SwaggerSpec(BaseModel):
    """Parsed Swagger/OpenAPI specification."""
    title: str
    version: str
    description: Optional[str] = None
    spec_type: SwaggerSpecType
    endpoints: List[SwaggerEndpoint] = []
    paths: Dict[str, Dict[str, Any]] = {}
    definitions: Dict[str, Any] = {}
    components: Dict[str, Any] = {}
    base_path: Optional[str] = None
    swagger_source: Optional[str] = None
    swagger_url: Optional[str] = None 