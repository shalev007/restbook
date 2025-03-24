"""Swagger/OpenAPI integration for RestBook."""

from .parser import SwaggerParser, SwaggerParserError
from .schema import (
    SwaggerSpec,
    SwaggerEndpoint,
    SwaggerEndpointParameter,
    SwaggerSpecType
)
from .client import (
    SwaggerClient,
    Swagger2Client,
    OpenAPI3Client,
    SwaggerClientFactory
)

__all__ = [
    # Parser
    "SwaggerParser",
    "SwaggerParserError",
    
    # Schema
    "SwaggerSpec",
    "SwaggerEndpoint",
    "SwaggerEndpointParameter",
    "SwaggerSpecType",
    
    # Client
    "SwaggerClient",
    "Swagger2Client",
    "OpenAPI3Client",
    "SwaggerClientFactory"
] 