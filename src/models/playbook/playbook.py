from typing import Dict, Any, Callable
import requests
import json
from .config import PlaybookConfig
from .validator import PlaybookYamlValidator
from ..session.session_store import SessionStore


class Playbook:
    """Represents a playbook that can be executed."""
    
    def __init__(self, config: PlaybookConfig, logger: Callable[[str], None] | None = None):
        """
        Initialize a playbook with a configuration.
        
        Args:
            config: The playbook configuration
            logger: Optional callback function for logging (e.g., click.echo)
        """
        self.config = config
        self.logger = logger or (lambda msg: None)

    @classmethod
    def from_yaml(cls, yaml_content: str, logger: Callable[[str], None] | None = None) -> 'Playbook':
        """
        Create a Playbook instance from YAML content.
        
        Args:
            yaml_content: The YAML content to parse
            logger: Optional callback function for logging
            
        Returns:
            Playbook: A new playbook instance
            
        Raises:
            ValueError: If the YAML content is invalid
        """
        config = PlaybookYamlValidator.validate_and_load(yaml_content)
        return cls(config, logger)

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

    def _log_response(self, step_number: int, response: requests.Response):
        """Log a response with its details."""
        self.logger(f"\nStep {step_number} Response:")
        self.logger(f"Status: {response.status_code}")
        self.logger("Headers:")
        for key, value in response.headers.items():
            self.logger(f"  {key}: {value}")
        self.logger("\nBody:")
        try:
            self.logger(json.dumps(response.json(), indent=2))
        except:
            self.logger(response.text)

    def execute(self, session_store: SessionStore) -> list[requests.Response]:
        """
        Execute the playbook using the provided session store.
        
        Args:
            session_store: The session store to use for execution
            
        Returns:
            list[requests.Response]: List of responses from each step
            
        Raises:
            ValueError: If the session does not exist
            requests.exceptions.RequestException: If any request fails
        """
        # Validate session exists
        sessions = session_store.list_sessions()
        if self.session_name not in sessions:
            raise ValueError(f"Session '{self.session_name}' does not exist")
        session = sessions[self.session_name]

        responses = []
        # Execute each step
        for i, step in enumerate(self.steps, 1):
            self.logger(f"\nExecuting step {i}...")
            
            # Prepare request
            url = f"{session.base_url.rstrip('/')}/{step.endpoint.lstrip('/')}"
            headers = {}
            if session.token:
                headers['Authorization'] = f"Bearer {session.token}"
            if step.headers:
                headers.update(step.headers)

            # Make request
            response = requests.request(
                method=step.method,
                url=url,
                headers=headers,
                json=step.data
            )
            responses.append(response)
            
            # Log response immediately
            self._log_response(i, response)

        return responses 