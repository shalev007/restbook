from typing import Dict, Any, List
from pydantic import ValidationError
from pydantic_core import ErrorDetails
import yaml
from .config import PlaybookConfig

def _build_validation_error_message(errors: List[ErrorDetails]) -> str:
    """Build a ValueError from a list of Pydantic validation errors."""
    messages = []
    for error in errors:
        field_path = " -> ".join(str(loc) for loc in error['loc'])
        msg = error['msg']
        messages.append(f"Error in field '{field_path}': {msg}")

    return "\n".join(messages)

class PlaybookYamlValidator:
    """Validates YAML content and creates PlaybookConfig instances."""

    @classmethod
    def validate_and_load(cls, yaml_content: str) -> PlaybookConfig:
        """
        Validate YAML content and create a PlaybookConfig instance.
        
        Args:
            yaml_content: The YAML content to validate
            
        Returns:
            PlaybookConfig: The validated playbook configuration
            
        Raises:
            ValueError: If the YAML content is invalid
        """
        try:
            # Parse YAML
            data = yaml.safe_load(yaml_content)
            
            # Use Pydantic model for validation
            return PlaybookConfig.model_validate(data)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {str(e)}")
        except ValidationError as e:
            raise ValueError(_build_validation_error_message(e.errors()))
        except Exception as e:
            raise ValueError(f"Invalid playbook format: {str(e)}") 