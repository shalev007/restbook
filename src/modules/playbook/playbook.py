import json
from typing import Dict, Any, Optional, List, Union
import asyncio
import jq  # type: ignore
from copy import deepcopy

from src.modules.session.session import Session

from .config import AuthType, PlaybookConfig, PhaseConfig, StepConfig, StoreConfig, RequestConfig, SessionConfig, AuthConfig, AuthCredentials
from .validator import PlaybookYamlValidator
from .template import TemplateRenderer
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
        self.variables: Dict[str, Any] = {}
        self.renderer = TemplateRenderer(logger)
        self._temp_sessions: Dict[str, Session] = {}

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

    def _render_session_config(self, session_config: SessionConfig) -> SessionConfig:
        """Render all template strings in a session configuration."""
        rendered_data: Dict[str, Union[str, Optional[AuthConfig]]] = {
            "base_url": self.renderer.render_template(session_config.base_url),
        }
        
        if session_config.auth:
            auth_data: Dict[str, Union[AuthType, Optional[AuthCredentials]]] = {
                "type": session_config.auth.type,
            }
            
            if session_config.auth.credentials:
                creds = session_config.auth.credentials
                rendered_creds: Dict[str, Union[str, List[str], None]] = {}
                
                # Render all credential fields that are set
                for field in creds.model_fields:
                    value = getattr(creds, field)
                    if value is not None:
                        if isinstance(value, str):
                            rendered_creds[field] = self.renderer.render_template(value)
                        elif isinstance(value, list):
                            rendered_creds[field] = [
                                self.renderer.render_template(item) if isinstance(item, str) else item
                                for item in value
                            ]
                        else:
                            rendered_creds[field] = value
                
                auth_data["credentials"] = AuthCredentials.model_validate(rendered_creds)
            
            rendered_data["auth"] = AuthConfig.model_validate(auth_data)
        
        return SessionConfig.model_validate(rendered_data)

    def _render_request_config(self, request: RequestConfig, context: Dict[str, Any]) -> RequestConfig:
        """Render all template strings in a request configuration."""
        rendered_data: Dict[str, Union[str, Optional[Dict[str, Any]]]] = {
            "method": request.method,
            "endpoint": self.renderer.render_template(request.endpoint, context),
            "data": self.renderer.render_dict(request.data, context) if request.data else None,
            "params": self.renderer.render_dict(request.params, context) if request.params else None,
            "headers": self.renderer.render_dict(request.headers, context) if request.headers else None
        }
        return RequestConfig.model_validate(rendered_data)
    
    def _render_store_config(self, store: StoreConfig, context: Dict[str, Any]) -> StoreConfig:
        """Render all template strings in a store configuration."""
        rendered_data: Dict[str, Union[str, Optional[str]]] = {
            "var": self.renderer.render_template(store.var, context),
            "jq": self.renderer.render_template(store.jq, context) if store.jq else None
        }
        return StoreConfig.model_validate(rendered_data)

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
            # Initialize temporary sessions if configured
            if self.config.sessions:
                for session_name, session_config in self.config.sessions.items():
                    rendered_config = self._render_session_config(session_config)
                    self._temp_sessions[session_name] = Session.from_dict(session_name, rendered_config.model_dump())
            
            # Execute phases
            for phase in self.config.phases:
                self.logger.log_info(f"Executing phase: {phase.name}")
                await self._execute_phase(phase, session_store)
        except Exception as e:
            self.logger.log_error(str(e))
            raise
        finally:
            # Clean up temporary sessions
            self._temp_sessions.clear()

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
            if step.iterate:
                # Parse iteration configuration
                var_name, collection_name = [x.strip() for x in step.iterate.split(" in ")]
                if collection_name not in self.variables:
                    raise ValueError(f"Iteration variable '{collection_name}' not found")
                
                collection = self.variables[collection_name]
                if not isinstance(collection, (list, dict)):
                    raise ValueError(f"Cannot iterate over {type(collection)}")

                # Create tasks for each item in collection
                tasks = []
                for item in (collection.items() if isinstance(collection, dict) else enumerate(collection)):
                    index, value = item
                    # Create context for template rendering
                    context = {
                        **self.variables,
                        var_name: value,
                        f"{var_name}_index": index
                    }
                    
                    # Create a copy of the step with rendered templates
                    rendered_step = step.model_copy(deep=True)
                    rendered_step.request = self._render_request_config(step.request, context)
                    if step.store:
                        rendered_step.store = [self._render_store_config(store, context) for store in step.store]
                    else:
                        rendered_step.store = None
                    
                    # Add task for this iteration
                    tasks.append(self._execute_single_step(rendered_step, session_store))

                # Execute iterations based on parallel flag
                if step.parallel:
                    self.logger.log_info(f"Executing {len(tasks)} iterations in parallel")
                    await asyncio.gather(*tasks)
                else:
                    self.logger.log_info(f"Executing {len(tasks)} iterations sequentially")
                    for task in tasks:
                        await task
            else:
                # Execute step directly if no iteration is configured
                await self._execute_single_step(step, session_store)

        except Exception as e:
            if step.on_error == "ignore":
                self.logger.log_info(f"Step failed but continuing: {str(e)}")
            else:
                raise

    async def _execute_single_step(self, step: StepConfig, session_store: SessionStore) -> None:
        """Execute a single step without iteration."""
        # Get session for this step
        if step.session in self._temp_sessions:
            session = self._temp_sessions[step.session]
        else:
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

        # Log response
        self.logger.log_status(response.status)
        try:
            body = await response.json()
            body_str = json.dumps(body, indent=2)
            
            # Store response data if configured
            if step.store:
                try:
                    await self._store_response_data(step.store, body, body_str)
                except Exception as e:
                    if step.on_error != "ignore":
                        raise
            
        except json.JSONDecodeError:
            body_str = await response.text()
        self.logger.log_body(body_str)

    async def _store_response_data(self, store_configs: List[StoreConfig], body: Dict[str, Any], body_str: str) -> None:
        """Store response data using configured JQ queries."""
        if not store_configs:
            return

        for store_config in store_configs:
            try:
                # Compile and execute JQ query
                query = jq.compile(store_config.jq) if store_config.jq else jq.compile('.')
                result = query.input(body).first()
                
                # Store the result
                self.variables[store_config.var] = result
                self.logger.log_info(f"Stored variable '{store_config.var}' = {json.dumps(result)}")
            except Exception as e:
                self.logger.log_error(f"Failed to store variable '{store_config.var}': {str(e)}")
                self.logger.log_error(f"Body: {body_str}")
                raise