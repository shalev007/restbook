import json
from typing import Dict, Any, Optional, List, Union
import jq  # type: ignore

from ..logging import BaseLogger
from .config import StoreConfig

class VariableManager:
    """Manages playbook variables, including storage and retrieval."""
    
    def __init__(self, logger: BaseLogger):
        """Initialize the variable manager."""
        self.variables: Dict[str, Any] = {}
        self.logger = logger
    
    def get(self, name: str, default: Any = None) -> Any:
        """Get a variable by name."""
        return self.variables.get(name, default)
    
    def set(self, name: str, value: Any) -> None:
        """Set a variable value."""
        self.variables[name] = value
        self.logger.log_info(f"Set variable '{name}' = {json.dumps(value)}")
    
    def has(self, name: str) -> bool:
        """Check if a variable exists."""
        return name in self.variables
    
    def get_all(self) -> Dict[str, Any]:
        """Get all variables."""
        return self.variables
    
    def set_all(self, variables: Dict[str, Any]) -> None:
        """Replace all variables."""
        self.variables = variables
        self.logger.log_info(f"Loaded {len(variables)} variables")
    
    def clear(self) -> None:
        """Clear all variables."""
        self.variables.clear()
        self.logger.log_info("Cleared all variables")
        
    async def store_response_data(self, store_configs: List[StoreConfig], body: Dict[str, Any]) -> Dict[str, Any]:
        """Store response data using configured JQ queries.
        
        Returns:
            Dict[str, Any]: Dictionary of variable names and their stored values
        """
        if not store_configs:
            return {}

        stored_vars = {}
        for store_config in store_configs:
            try:
                # Compile and execute JQ query
                query = jq.compile(store_config.jq) if store_config.jq else jq.compile('.')
                result = query.input(body).first()
                
                # Handle append mode
                if store_config.append:
                    self._append_value(store_config.var, result)
                else:
                    # Normal replacement mode
                    self.set(store_config.var, result)
                
                # Store the result in our return dict
                stored_vars[store_config.var] = result
                
            except Exception as e:
                body_str = json.dumps(body, indent=2)
                self.logger.log_error(f"Failed to store variable '{store_config.var}': {str(e)}")
                self.logger.log_error(f"Body: {body_str}")
                raise
                
        return stored_vars
    
    def _append_value(self, var_name: str, value: Any) -> None:
        """Append a value to a variable, creating a list if needed."""
        if not self.has(var_name):
            # Initialize as a new list
            self.variables[var_name] = [value]
            self.logger.log_info(f"Created list variable '{var_name}' with first item")
        else:
            # Ensure it's a list
            if not isinstance(self.variables[var_name], list):
                # Convert existing value to a list with the original value as first item
                self.variables[var_name] = [self.variables[var_name]]
                self.logger.log_info(f"Converted '{var_name}' to list")
            
            # Append the new result
            self.variables[var_name].append(value)
            self.logger.log_info(f"Appended to list variable '{var_name}', now has {len(self.variables[var_name])} items") 