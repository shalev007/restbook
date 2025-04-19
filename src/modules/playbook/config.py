from enum import Enum
from typing import List, Dict, Any

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, model_validator

class MethodConfig(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

class AuthType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    OAUTH2 = "oauth2"

class AuthCredentials(BaseModel):
    # Bearer token auth
    token: Optional[str] = None
    
    # Basic auth
    username: Optional[str] = None
    password: Optional[str] = None
    
    # OAuth2 auth
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[str] = None
    scopes: Optional[List[str]] = None

class AuthConfig(BaseModel):
    type: AuthType = AuthType.NONE
    credentials: Optional[AuthCredentials] = None


class RequestConfig(BaseModel):
    method: MethodConfig = MethodConfig.GET  # Defaults to GET if not provided.
    endpoint: str
    data: Optional[Dict[str, Any]] = None
    fromFile: Optional[str] = None  # Path to JSON file containing request data
    params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, Any]] = None

    @model_validator(mode='after')
    def validate_data_sources(self) -> 'RequestConfig':
        """Validate that only one data source is specified."""
        if self.data is not None and self.fromFile is not None:
            raise ValueError("Cannot specify both 'data' and 'fromFile' in the same request")
        return self

class StoreConfig(BaseModel):
    var: str
    jq: Optional[str] = None  # JQ query to extract data from response
    append: bool = False  # If true, append to list instead of replacing value

class CircuitBreakerConfig(BaseModel):
    threshold: int = 2  # number of failures before opening the circuit
    reset: int = 10     # seconds to wait before resetting circuit breaker
    jitter: float = 0.0  # random jitter factor (0.0 to 1.0) to add to reset time

class RateLimitConfig(BaseModel):
    use_server_retry_delay: bool = True
    retry_header: str = "Retry-After"

class RetryConfig(BaseModel):
    max_retries: int = 2
    backoff_factor: float = 1.0
    max_delay: Optional[int] = None
    circuit_breaker: Optional[CircuitBreakerConfig] = None
    rate_limit: RateLimitConfig = RateLimitConfig()

    @model_validator(mode='after')
    def validate_circuit_breaker(self) -> 'RetryConfig':
        if self.circuit_breaker:
            if self.max_retries is None:
                raise ValueError("max_retries is required when circuit_breaker is provided")
            if self.circuit_breaker.threshold is None:
                raise ValueError("circuit_breaker.threshold is required when circuit_breaker is provided")
            if self.max_retries < self.circuit_breaker.threshold:
                raise ValueError("max_retries must be greater than or equal to circuit_breaker.threshold")
        return self

class OnErrorConfig(str, Enum):
    IGNORE = "ignore"
    ABORT = "abort"

class SessionConfig(BaseModel):
    base_url: str
    auth: Optional[AuthConfig] = None
    retry: Optional[RetryConfig] = None
    validate_ssl: bool = True
    timeout: int = 30

class StepConfig(BaseModel):
    session: str
    iterate: Optional[str] = None
    parallel: Optional[bool] = False  # Whether to execute iterations in parallel
    request: RequestConfig  # Use our nested model for request details.
    store: Optional[List[StoreConfig]] = None
    retry: Optional[RetryConfig] = None
    validate_ssl: bool = True
    timeout: int = 30
    on_error: Optional[OnErrorConfig] = OnErrorConfig.ABORT

class PhaseConfig(BaseModel):
    name: str
    parallel: Optional[bool] = False  # Default to sequential execution.
    steps: List[StepConfig]

class IncrementalStoreType(str, Enum):
    FILE = "file"

class IncrementalConfig(BaseModel):
    enabled: bool = False
    store: IncrementalStoreType = IncrementalStoreType.FILE
    file_path: Optional[str] = None

    @model_validator(mode='after')
    def validate_file_store(self) -> 'IncrementalConfig':
        """Validate the file store configuration."""
        if not self.enabled:
            return self
        if self.store == IncrementalStoreType.FILE and not self.file_path:
            raise ValueError("file_path is required when store type is 'file'")
        return self

class MetricsCollectorType(str, Enum):
    JSON = "json"
    PROMETHEUS = "prometheus"
    CONSOLE = "console"

class MetricsConfig(BaseModel):
    enabled: bool = False
    collector: MetricsCollectorType = MetricsCollectorType.JSON
    # JSON collector specific config
    output_file: Optional[str] = None
    # Prometheus collector specific config
    push_gateway: Optional[str] = None
    job_name: str = "restbook"
    # Console collector specific config
    verbosity: str = "info"  # debug, info, warning

    @model_validator(mode='after')
    def validate_collector_config(self) -> 'MetricsConfig':
        """Validate collector-specific configuration."""
        if not self.enabled:
            return self
            
        if self.collector == MetricsCollectorType.JSON and not self.output_file:
            raise ValueError("output_file is required when using JSON collector")
            
        if self.collector == MetricsCollectorType.PROMETHEUS and not self.push_gateway:
            raise ValueError("push_gateway is required when using Prometheus collector")
            
        return self

class PlaybookConfig(BaseModel):
    sessions: Optional[Dict[str, SessionConfig]] = None  # Make sessions optional
    phases: List[PhaseConfig]
    incremental: Optional[IncrementalConfig] = IncrementalConfig()  # Default to disabled
    metrics: Optional[MetricsConfig] = MetricsConfig()  # Default to disabled
    shutdown_timeout: float = 2.0  # Default timeout for graceful shutdown in seconds