import os
from typing import Dict, Any, Optional, List, Union
from jinja2 import Template  # type: ignore
from ..logging import BaseLogger

# Type aliases for template rendering
TemplateValue = Union[str, Dict[str, Any], List[Any]]
RenderableDict = Dict[str, TemplateValue]

class TemplateRenderer:
    """Handles template rendering with environment variable support."""
    
    def __init__(self, logger: BaseLogger):
        """
        Initialize the template renderer.
        
        Args:
            logger: Logger instance for error reporting
        """
        self.logger = logger
        self._template_cache: Dict[str, Template] = {}
        
    def _get_template(self, template_str: str) -> Template:
        """Get a cached template or compile and cache it."""
        if template_str not in self._template_cache:
            self._template_cache[template_str] = Template(str(template_str))
        return self._template_cache[template_str]
    
    def _get_env_var(self, var_name: str) -> Optional[str]:
        """Get an environment variable value."""
        return os.environ.get(var_name)
    
    def render_template(self, template_str: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Render a template string with the given context and environment variables.
        
        Args:
            template_str: The template string to render
            context: Optional context dictionary for rendering
            
        Returns:
            str: The rendered string
            
        Raises:
            Exception: If template rendering fails
        """
        try:
            if not template_str:
                return template_str
                
            # Create context with environment variables if needed
            render_context = context or {}
            if "{{" in template_str and "}}" in template_str and "env." in template_str:
                env_vars = {}
                # Simple env var extraction - can be improved if needed
                for var in template_str.split("{{"):
                    if "}}" in var and "env." in var:
                        env_name = var.split("env.")[1].split("}}")[0].strip()
                        env_vars[env_name] = self._get_env_var(env_name)
                render_context = {**render_context, "env": env_vars}
            
            template = self._get_template(template_str)
            return template.render(**render_context)
        except Exception as e:
            self.logger.log_error(f"Failed to render template '{template_str}': {str(e)}")
            raise
    
    def render_dict(self, data: RenderableDict, context: Optional[Dict[str, Any]] = None) -> RenderableDict:
        """
        Recursively render all string values in a dictionary.
        
        Args:
            data: The dictionary to render
            context: Optional context dictionary for rendering
            
        Returns:
            RenderableDict: The rendered dictionary
        """
        if not data:
            return data
            
        result: RenderableDict = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.render_template(value, context)
            elif isinstance(value, dict):
                result[key] = self.render_dict(value, context)
            elif isinstance(value, list):
                result[key] = [
                    self.render_dict(item, context) if isinstance(item, dict)
                    else self.render_template(item, context) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result 