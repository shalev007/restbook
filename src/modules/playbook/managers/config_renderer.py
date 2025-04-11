from typing import Dict, Any, Optional, List, Union
import os
import json

from ..config import (
    SessionConfig, RequestConfig, StoreConfig, AuthConfig, AuthCredentials,
    AuthType
)
from ..template_renderer import TemplateRenderer
from ..variables import VariableManager

class ConfigRenderer:
    """Handles rendering of configuration objects with templates and variables."""
    
    def __init__(self, renderer: TemplateRenderer, variables: VariableManager):
        """
        Initialize the config renderer.
        
        Args:
            renderer: Template renderer for handling template strings
            variables: Variable manager for accessing variables
        """
        self.renderer = renderer
        self.variables = variables

    def render_session_config(self, config: SessionConfig) -> SessionConfig:
        """
        Render a session configuration with current variables.
        
        Args:
            config: The session configuration to render
            
        Returns:
            SessionConfig: The rendered configuration
        """
        context = self.variables.get_all()
        
        # Render base URL
        rendered_data: Dict[str, Any] = {
            "base_url": self.renderer.render_template(config.base_url, context),
        }
        
        # Render auth if present
        if config.auth:
            auth_data: Dict[str, Any] = {
                "type": config.auth.type,
            }
            
            if config.auth.credentials:
                creds = config.auth.credentials
                rendered_creds: Dict[str, Any] = {}
                
                # Render all credential fields that are set
                for field in creds.model_fields:
                    value = getattr(creds, field)
                    if value is not None:
                        if isinstance(value, str):
                            rendered_creds[field] = self.renderer.render_template(value, context)
                        elif isinstance(value, list) and field == "scopes":
                            rendered_creds[field] = [
                                self.renderer.render_template(item, context) if isinstance(item, str) else item
                                for item in value
                            ]
                        else:
                            rendered_creds[field] = value
                
                auth_data["credentials"] = AuthCredentials.model_validate(rendered_creds)
            
            rendered_data["auth"] = AuthConfig.model_validate(auth_data)
        
        return SessionConfig.model_validate(rendered_data)

    def render_request_config(self, config: RequestConfig, extra_vars: Dict[str, Any]) -> RequestConfig:
        """
        Render a request configuration with current variables and context.
        
        Args:
            config: The request configuration to render
            extra_vars: Additional variables to include in the context
            
        Returns:
            RequestConfig: The rendered configuration
        """
        # Merge global variables with step context
        context = {**self.variables.get_all(), **extra_vars}
        
        # Handle loading data from file if specified
        data = None
        if config.fromFile:
            # Render the file path with variables/templates
            file_path = self.renderer.render_template(config.fromFile, context)
            
            # Support both absolute paths and paths relative to the working directory
            if not os.path.isabs(file_path):
                file_path = os.path.join(os.getcwd(), file_path)
                
            try:
                # Read and parse the JSON file
                with open(file_path, 'r') as f:
                    file_content = f.read()
                    
                # Parse the file content as JSON
                data = json.loads(file_content)
                
                # Render templates in the loaded data
                data = self.renderer.render_dict(data, context)
            except FileNotFoundError:
                raise ValueError(f"Request data file not found: {file_path}")
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON in request data file: {file_path}")
            except Exception as e:
                raise ValueError(f"Error loading request data from file {file_path}: {str(e)}")
        else:
            # Use inline data if specified
            data = self.renderer.render_dict(config.data, context) if config.data else None
        
        rendered_data: Dict[str, Any] = {
            "method": config.method,
            "endpoint": self.renderer.render_template(config.endpoint, context),
            "data": data,
            "params": self.renderer.render_dict(config.params, context) if config.params else None,
            "headers": self.renderer.render_dict(config.headers, context) if config.headers else None,
            "fromFile": None  # Don't include fromFile in the rendered config
        }
        
        return RequestConfig.model_validate(rendered_data)

    def render_store_config(self, config: StoreConfig, extra_vars: Dict[str, Any]) -> StoreConfig:
        """
        Render a store configuration with current variables and context.
        
        Args:
            config: The store configuration to render
            extra_vars: Additional variables to include in the context
            
        Returns:
            StoreConfig: The rendered configuration
        """
        # Merge global variables with step context
        context = {**self.variables.get_all(), **extra_vars}
        
        rendered_data: Dict[str, Any] = {
            "var": self.renderer.render_template(config.var, context),
            "jq": self.renderer.render_template(config.jq, context) if config.jq else None,
            "append": config.append
        }
        
        return StoreConfig.model_validate(rendered_data) 