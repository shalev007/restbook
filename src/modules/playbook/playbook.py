import json
from typing import Dict, Any, Optional, List
import asyncio
from .config import PlaybookConfig, PhaseConfig, StepConfig
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert the playbook to a dictionary."""
        return self.config.model_dump()

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
            for phase in self.config.phases:
                self.logger.log_info(f"Executing phase: {phase.name}")
                await self._execute_phase(phase, session_store)
        except Exception as e:
            self.logger.log_error(str(e))
            raise

    async def _execute_phase(self, phase: PhaseConfig, session_store: SessionStore) -> None:
        """Execute a single phase of the playbook."""
        if phase.parallel:
            # Execute steps in parallel
            tasks = [
                self._execute_step(step, session_store)
                for step in phase.steps
            ]
            await asyncio.gather(*tasks)
        else:
            # Execute steps sequentially
            for step in phase.steps:
                await self._execute_step(step, session_store)

    async def _execute_step(self, step: StepConfig, session_store: SessionStore) -> None:
        """Execute a single step of the playbook."""
        try:
            # Get session for this step
            session = session_store.get_session(step.session)

            # Create request executor with step-specific config
            executor = RequestExecutor(
                session=session,
                timeout=(step.retry and step.retry.timeout) or 30,
                verify_ssl=step.validate_ssl if step.validate_ssl is not None else True,
                max_retries=(step.retry and step.retry.max_retries) or 3,
                backoff_factor=(step.retry and step.retry.backoff_factor) or 0.5
            )

            # Execute request
            response = await executor.execute_request(
                method=step.request.method.value,
                endpoint=step.request.endpoint,
                headers=step.request.headers,
                data=step.request.data
            )

            # TODO: Handle response storage in variables when store config is present
            # TODO: Handle iteration over variables when iterate is present

            # log response
            self.logger.log_status(response.status)
            try:
                body = await response.json()
                body_str = json.dumps(body, indent=2)
            except:
                body_str = await response.text()
            self.logger.log_body(body_str)

        except Exception as e:
            if step.on_error == "ignore":
                self.logger.log_info(f"Step failed but continuing: {str(e)}")
            else:
                raise