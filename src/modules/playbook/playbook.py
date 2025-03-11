import json
from typing import Dict, Any, Optional, List, Union
import asyncio
import jq  # type: ignore
from jinja2 import Template
from .config import PlaybookConfig, PhaseConfig, StepConfig, StoreConfig, RequestConfig
from .validator import PlaybookYamlValidator
from ..session.session_store import SessionStore
from ..logging import BaseLogger
from ..request.executor import RequestExecutor

# Type aliases for template rendering
TemplateValue = Union[str, Dict[str, Any], List[Any]]
RenderableDict = Dict[str, TemplateValue]

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
        self._template_cache: Dict[str, Template] = {}

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

    def _get_template(self, template_str: str) -> Template:
        """Get a cached template or compile and cache it."""
        if template_str not in self._template_cache:
            self._template_cache[template_str] = Template(str(template_str))
        return self._template_cache[template_str]

    def _render_template(self, template_str: str, context: Dict[str, Any]) -> str:
        """Render a Jinja2 template string with the given context."""
        try:
            template = self._get_template(template_str)
            return template.render(**context)
        except Exception as e:
            self.logger.log_error(f"Failed to render template '{template_str}': {str(e)}")
            raise

    def _render_dict(self, data: RenderableDict, context: Dict[str, Any]) -> RenderableDict:
        """Recursively render all string values in a dictionary using Jinja2."""
        result: RenderableDict = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._render_template(value, context)
            elif isinstance(value, dict):
                result[key] = self._render_dict(value, context)
            elif isinstance(value, list):
                result[key] = [
                    self._render_dict(item, context) if isinstance(item, dict)
                    else self._render_template(item, context) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _render_request_config(self, request: RequestConfig, context: Dict[str, Any]) -> RequestConfig:
        """Render all template strings in a request configuration."""
        rendered_data = {
            "method": request.method,
            "endpoint": self._render_template(request.endpoint, context),
            "data": self._render_dict(request.data, context) if request.data else None,
            "params": self._render_dict(request.params, context) if request.params else None,
            "headers": self._render_dict(request.headers, context) if request.headers else None
        }
        return RequestConfig.model_validate(rendered_data)
    
    def _render_store_config(self, store: StoreConfig, context: Dict[str, Any]) -> StoreConfig:
        """Render all template strings in a store configuration."""
        rendered_data = {
            "var": self._render_template(store.var, context),
            "jq": self._render_template(store.jq, context) if store.jq else None
        }
        return StoreConfig.model_validate(rendered_data)
    
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

                # Execute step for each item in collection
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
                    
                    # Execute the rendered step
                    await self._execute_single_step(rendered_step, session_store)
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