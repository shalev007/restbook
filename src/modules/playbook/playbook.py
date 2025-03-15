import json
import hashlib
from typing import Dict, Any, Optional, List, Union
import asyncio
import jq  # type: ignore

from src.modules.session.session import Session

from .config import AuthType, PlaybookConfig, PhaseConfig, StepConfig, StoreConfig, RequestConfig, SessionConfig, AuthConfig, AuthCredentials, IncrementalConfig
from .validator import PlaybookYamlValidator
from .template import TemplateRenderer
from .checkpoint import CheckpointStore, CheckpointData, create_checkpoint_store
from .variables import VariableManager
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
        self.variables = VariableManager(logger)
        self.renderer = TemplateRenderer(logger)
        self._temp_sessions: Dict[str, Session] = {}
        
        # Initialize checkpoint store if incremental execution is enabled
        self.checkpoint_store: Optional[CheckpointStore] = None
        self.content_hash: Optional[str] = None
        
        if self.config.incremental and self.config.incremental.enabled:
            self.content_hash = self._generate_content_hash()
            self.checkpoint_store = create_checkpoint_store(self.config.incremental)
            logger.log_info(f"Incremental execution enabled. Content hash: {self.content_hash}")

    def _generate_content_hash(self) -> str:
        """Generate a hash of the playbook content."""
        # Convert config to JSON string
        config_str = json.dumps(self.config.model_dump(exclude={"incremental"}), sort_keys=True)
        # Generate hash
        return hashlib.md5(config_str.encode()).hexdigest()

    async def _save_checkpoint(self, phase_index: int, step_index: int) -> None:
        """Save execution checkpoint."""
        if not self.checkpoint_store or not self.content_hash:
            return
            
        try:
            checkpoint = CheckpointData(
                current_phase=phase_index,
                current_step=step_index,
                variables=self.variables.get_all(),
                content_hash=self.content_hash
            )
            
            await self.checkpoint_store.save(checkpoint)
            self.logger.log_info(f"Checkpoint saved: Phase {phase_index}, Step {step_index}")
        except Exception as e:
            self.logger.log_error(f"Failed to save checkpoint: {str(e)}")

    async def _load_checkpoint(self) -> Optional[CheckpointData]:
        """Load execution checkpoint."""
        if not self.checkpoint_store or not self.content_hash:
            return None
            
        try:
            checkpoint = await self.checkpoint_store.load(self.content_hash)
            if checkpoint:
                self.logger.log_info(f"Checkpoint loaded: Phase {checkpoint.current_phase}, Step {checkpoint.current_step}")
                # Restore variables
                self.variables.set_all(checkpoint.variables)
            return checkpoint
        except Exception as e:
            self.logger.log_error(f"Failed to load checkpoint: {str(e)}")
            return None

    async def _clear_checkpoint(self) -> None:
        """Clear execution checkpoint."""
        if not self.checkpoint_store or not self.content_hash:
            return
            
        try:
            await self.checkpoint_store.clear(self.content_hash)
            self.logger.log_info("Checkpoint cleared")
        except Exception as e:
            self.logger.log_error(f"Failed to clear checkpoint: {str(e)}")

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
        # Get variables for template context
        context = self.variables.get_all()
        
        rendered_data: Dict[str, Union[str, Optional[AuthConfig]]] = {
            "base_url": self.renderer.render_template(session_config.base_url, context),
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
                            rendered_creds[field] = self.renderer.render_template(value, context)
                        elif isinstance(value, list):
                            rendered_creds[field] = [
                                self.renderer.render_template(item, context) if isinstance(item, str) else item
                                for item in value
                            ]
                        else:
                            rendered_creds[field] = value
                
                auth_data["credentials"] = AuthCredentials.model_validate(rendered_creds)
            
            rendered_data["auth"] = AuthConfig.model_validate(auth_data)
        
        return SessionConfig.model_validate(rendered_data)

    def _render_request_config(self, request: RequestConfig, step_context: Dict[str, Any]) -> RequestConfig:
        """Render all template strings in a request configuration."""
        # Merge step context with global variables
        context = {**self.variables.get_all(), **step_context}
        
        rendered_data: Dict[str, Union[str, Optional[Dict[str, Any]]]] = {
            "method": request.method,
            "endpoint": self.renderer.render_template(request.endpoint, context),
            "data": self.renderer.render_dict(request.data, context) if request.data else None,
            "params": self.renderer.render_dict(request.params, context) if request.params else None,
            "headers": self.renderer.render_dict(request.headers, context) if request.headers else None
        }
        return RequestConfig.model_validate(rendered_data)
    
    def _render_store_config(self, store: StoreConfig, step_context: Dict[str, Any]) -> StoreConfig:
        """Render all template strings in a store configuration."""
        # Merge step context with global variables
        context = {**self.variables.get_all(), **step_context}
        
        rendered_data: Dict[str, Union[str, Optional[str], bool]] = {
            "var": self.renderer.render_template(store.var, context),
            "jq": self.renderer.render_template(store.jq, context) if store.jq else None,
            "append": store.append
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
            # Check for checkpoint if incremental is enabled
            checkpoint = None
            if self.checkpoint_store and self.content_hash:
                checkpoint = await self._load_checkpoint()
            
            # Initialize temporary sessions if configured
            if self.config.sessions:
                for session_name, session_config in self.config.sessions.items():
                    rendered_config = self._render_session_config(session_config)
                    self._temp_sessions[session_name] = Session.from_dict(session_name, rendered_config.model_dump())
            
            # Execute phases
            for phase_index, phase in enumerate(self.config.phases):
                # Skip phases before checkpoint
                if checkpoint and phase_index < checkpoint.current_phase:
                    self.logger.log_info(f"Skipping phase {phase_index}: {phase.name} (already completed)")
                    continue
                    
                self.logger.log_info(f"Executing phase {phase_index}: {phase.name}")
                
                if phase.parallel:
                    # For parallel execution, we need to handle checkpoints differently
                    if checkpoint and phase_index == checkpoint.current_phase:
                        # This is the phase where we left off - we need to re-run it completely
                        # since we can't guarantee which steps completed in parallel execution
                        self.logger.log_info("Restarting parallel phase from beginning")
                        checkpoint = None
                    
                    # Execute steps in parallel
                    tasks = [
                        self._execute_step(step, session_store)
                        for step in phase.steps
                    ]
                    await asyncio.gather(*tasks)
                    
                    # Save checkpoint after parallel phase
                    await self._save_checkpoint(phase_index, len(phase.steps) - 1)
                else:
                    # Execute steps sequentially
                    for step_index, step in enumerate(phase.steps):
                        # Skip steps before checkpoint in the current phase
                        if checkpoint and phase_index == checkpoint.current_phase and step_index <= checkpoint.current_step:
                            self.logger.log_info(f"Skipping step {step_index} (already completed)")
                            continue
                            
                        await self._execute_step(step, session_store)
                        
                        # Save checkpoint after each step
                        await self._save_checkpoint(phase_index, step_index)
            
            # Clear checkpoint after successful execution
            await self._clear_checkpoint()
            
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
                if not self.variables.has(collection_name):
                    raise ValueError(f"Iteration variable '{collection_name}' not found")
                
                collection = self.variables.get(collection_name)
                if not isinstance(collection, (list, dict)):
                    raise ValueError(f"Cannot iterate over {type(collection)}")

                # Create tasks for each item in collection
                tasks = []
                for item in (collection.items() if isinstance(collection, dict) else enumerate(collection)):
                    index, value = item
                    # Create context for template rendering
                    context = {
                        **self.variables.get_all(),
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
                    await self.variables.store_response_data(step.store, body)
                except Exception as e:
                    if step.on_error != "ignore":
                        raise
            
        except json.JSONDecodeError:
            body_str = await response.text()
        self.logger.log_body(body_str)