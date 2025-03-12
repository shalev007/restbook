from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any

from typing import Optional, Dict, Any, List
from pydantic import BaseModel

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

class SessionConfig(BaseModel):
    base_url: str
    auth: Optional[AuthConfig] = None

class RequestConfig(BaseModel):
    method: MethodConfig = MethodConfig.GET  # Defaults to GET if not provided.
    endpoint: str
    data: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, Any]] = None

class StoreConfig(BaseModel):
    var: str
    jq: Optional[str] = None  # JQ query to extract data from response

class RetryConfig(BaseModel):
    max_retries: Optional[int] = 3
    backoff_factor: Optional[float] = 1.0
    timeout: Optional[int] = 10

class OnErrorConfig(str, Enum):
    IGNORE = "ignore"
    ABORT = "abort"

class StepConfig(BaseModel):
    session: str
    iterate: Optional[str] = None
    parallel: Optional[bool] = False  # Whether to execute iterations in parallel
    request: RequestConfig  # Use our nested model for request details.
    store: Optional[List[StoreConfig]] = None
    retry: Optional[RetryConfig] = None
    validate_ssl: Optional[bool] = True
    on_error: Optional[OnErrorConfig] = OnErrorConfig.ABORT

class PhaseConfig(BaseModel):
    name: str
    parallel: Optional[bool] = False  # Default to sequential execution.
    steps: List[StepConfig]

class PlaybookConfig(BaseModel):
    sessions: Optional[Dict[str, SessionConfig]] = None  # Make sessions optional
    phases: List[PhaseConfig]