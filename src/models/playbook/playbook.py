from typing import Dict, Any
from .config import PlaybookConfig
from .validator import PlaybookYamlValidator


class Playbook:
    """Represents a playbook that can be executed."""
    
    def __init__(self, config: PlaybookConfig):
        """
        Initialize a playbook with a configuration.
        
        Args:
            config: The playbook configuration
        """
        self.config = config

    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'Playbook':
        """
        Create a Playbook instance from YAML content.
        
        Args:
            yaml_content: The YAML content to parse
            
        Returns:
            Playbook: A new playbook instance
            
        Raises:
            ValueError: If the YAML content is invalid
        """
        config = PlaybookYamlValidator.validate_and_load(yaml_content)
        return cls(config)

    @property
    def session_name(self) -> str:
        """Get the session name."""
        return self.config.session_name

    @property
    def steps(self) -> list:
        """Get the playbook steps."""
        return self.config.steps

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Playbook to a dictionary."""
        return {
            "session": self.session_name,
            "steps": [
                {
                    "method": step.method,
                    "endpoint": step.endpoint,
                    **({"headers": step.headers} if step.headers else {}),
                    **({"data": step.data} if step.data else {})
                }
                for step in self.steps
            ]
        } 