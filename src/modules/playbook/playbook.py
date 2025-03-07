from typing import Dict, Any, Optional, List
import asyncio
import aiohttp
import json
from .config import PlaybookConfig, PlaybookStep
from .validator import PlaybookYamlValidator
from ..session.session_store import SessionStore
from ..logging import BaseLogger
from ..request.executor import RequestExecutor


class Playbook:
    """Represents a playbook that can be executed."""
    
    def __init__(self, config: PlaybookConfig, logger: BaseLogger):
        """
        Initialize a playbook with a configuration.
        
        Args:
            config: The playbook configuration
            logger: Logger instance for request/response logging
        """
        self.config = config
        self.logger = logger

    @classmethod
    def from_yaml(cls, yaml_content: str, logger: BaseLogger) -> 'Playbook':
        """
        Create a Playbook instance from YAML content.
        
        Args:
            yaml_content: The YAML content to parse
            logger: Logger instance for request/response logging
            
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
    def steps(self) -> List[PlaybookStep]:
        """Get the playbook steps."""
        return self.config.steps

    def to_dict(self) -> Dict[str, Any]:
        """Convert the playbook to a dictionary."""
        return {
            "session_name": self.session_name,
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

    async def execute(self, session_store: SessionStore) -> None:
        """
        Execute the playbook using the provided session store.
        
        Args:
            session_store: The session store to use for execution
            
        Raises:
            ValueError: If the session does not exist
            aiohttp.ClientError: If any request fails
        """
        try:
            # Validate session exists
            sessions = session_store.list_sessions()
            if self.session_name not in sessions:
                error_msg = f"Session '{self.session_name}' does not exist"
                self.logger.log_error(error_msg)
                raise ValueError(error_msg)
            session = sessions[self.session_name]

            # Create request executor for this playbook execution
            executor = RequestExecutor(
                session=session,
                # Use default values for timeout, verify_ssl, max_retries, and backoff_factor
            )

            responses: List[aiohttp.ClientResponse] = []
            # Execute each step
            for i, step in enumerate(self.steps, 1):
                self.logger.log_step(i, step.method, step.endpoint)
                
                try:
                    # Convert step headers to JSON string if present
                    headers_str = json.dumps(step.headers) if step.headers else None
                    # Convert step data to JSON string if present
                    data_str = json.dumps(step.data) if step.data else None

                    # Execute request using executor
                    response = await executor.execute_request(
                        method=step.method,
                        endpoint=step.endpoint,
                        headers=headers_str,
                        data=data_str
                    )
                    
                    # Log response
                    await self._log_response(i, response)
                    
                except (ValueError, aiohttp.ClientError) as err:
                    self.logger.log_error(f"Step {i} failed: {str(err)}")
                    raise
        except Exception as err:
            self.logger.log_error(str(err))
            raise

    async def _log_response(self, step_number: int, response: aiohttp.ClientResponse) -> None:
        """Log the response for a step."""
        self.logger.log_status(response.status)
        self.logger.log_headers(dict(response.headers))
        try:
            body = await response.json()
            body_str = json.dumps(body, indent=2)
        except:
            body_str = await response.text()
        self.logger.log_body(body_str) 