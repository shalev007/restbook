import json
from typing import Dict, Any, List
import asyncio

from .config import (
    PlaybookConfig, StepConfig
)
from .validator import PlaybookYamlValidator
from .template_renderer import TemplateRenderer
from .variables import VariableManager
from .managers.config_renderer import ConfigRenderer
from .managers.checkpoint_manager import CheckpointManager
from .managers.session_manager import SessionManager
from .managers.observer_manager import ObserverManager
from .managers.execution_tracker import ExecutionTracker
from ..session.session_store import SessionStore
from ..logging import BaseLogger
from ..request.resilient_http_client import HttpRequestSpec
from ..request.client_factory import ResilientHttpClientFactory
from .observer.events import (
    PlaybookStartEvent, PlaybookEndEvent,
    PhaseStartEvent, PhaseEndEvent,
    StepStartEvent, StepEndEvent,
    RequestStartEvent, RequestEndEvent
)
from .context.execution_context import PhaseContext, RequestContext, StepContext

class Playbook:
    """Represents a playbook that can be executed."""
    
    def __init__(self,
                 config: PlaybookConfig,
                 logger: BaseLogger,
                 variables: VariableManager,
                 renderer: TemplateRenderer,
                 config_renderer: ConfigRenderer,
                 checkpoint_manager: CheckpointManager,
                 session_manager: SessionManager,
                 observer_manager: ObserverManager,
                 client_factory: ResilientHttpClientFactory):
        """
        Initialize a playbook with its dependencies.
        
        Args:
            config: The playbook configuration
            logger: Logger instance for request/response logging
            variables: Manager for handling variables
            renderer: Template renderer for processing templates
            config_renderer: Renders configuration with variables
            checkpoint_manager: Manages execution checkpoints
            session_manager: Manages HTTP sessions
            observer_manager: Manages execution observers
            client_factory: Factory for creating HTTP clients
        """
        self.config = config
        self.logger = logger
        self.variables = variables
        self.renderer = renderer
        self.config_renderer = config_renderer
        self.checkpoint_manager = checkpoint_manager
        self.session_manager = session_manager
        self.observer_manager = observer_manager
        self.client_factory = client_factory
        self.tracker = ExecutionTracker()
        # Track all running request tasks for graceful shutdown
        self._running_requests: List[asyncio.Task] = []
        self._cleanup_done = False
        self._current_phase_index = 0
        self._current_step_index = 0

    @classmethod
    def create(cls, config: PlaybookConfig, logger: BaseLogger, session_store: SessionStore) -> 'Playbook':
        """
        Factory method to create a Playbook instance with default dependencies.
        
        Args:
            config: The playbook configuration
            logger: Logger instance for request/response logging
            session_store: Store for managing HTTP sessions
            
        Returns:
            Playbook: A new playbook instance with default dependencies
        """
        variables = VariableManager(logger)
        renderer = TemplateRenderer(logger)
        config_renderer = ConfigRenderer(renderer, variables)
        checkpoint_manager = CheckpointManager(config, logger)
        session_manager = SessionManager(config_renderer, logger, session_store)
        observer_manager = ObserverManager(config, logger)
        client_factory = ResilientHttpClientFactory(logger)
        
        return cls(
            config=config,
            logger=logger,
            variables=variables,
            renderer=renderer,
            config_renderer=config_renderer,
            checkpoint_manager=checkpoint_manager,
            session_manager=session_manager,
            observer_manager=observer_manager,
            client_factory=client_factory
        )

    @classmethod
    def from_yaml(cls, yaml_content: str, logger: BaseLogger, session_store: SessionStore) -> 'Playbook':
        """
        Create a Playbook instance from YAML content.
        
        Args:
            yaml_content: The YAML content to parse
            logger: Logger instance for request/response logging
            session_store: Store for managing HTTP sessions
            
        Returns:
            Playbook: A new playbook instance
            
        Raises:
            ValueError: If the YAML content is invalid
        """
        config = PlaybookYamlValidator.validate_and_load(yaml_content)
        return cls.create(config, logger, session_store)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the playbook to a dictionary."""
        return self.config.model_dump()

    async def cancel_and_cleanup(self) -> None:
        """
        Cancel any running requests and clean up resources.
        This is safe to call multiple times.
        """
        if self.tracker.cleanup_done:
            return
            
        self.logger.log_info("Gracefully cleaning up playbook execution...")
        
        # Cancel any running requests
        active_requests = list(self.tracker.running_requests)  # Make a copy
        for task in active_requests:
            if not task.done():
                self.logger.log_info(f"Cancelling in-progress request")
                task.cancel()
        
        # Wait for cancellations to complete (with timeout)
        if active_requests:
            try:
                # Use configured timeout or default
                timeout = self.config.shutdown_timeout
                self.logger.log_info(f"Waiting up to {timeout} seconds for requests to complete...")
                await asyncio.wait(active_requests, timeout=timeout, return_when=asyncio.ALL_COMPLETED)
            except Exception as e:
                self.logger.log_warning(f"Error waiting for request cancellation: {str(e)}")
        
        # Save checkpoint of current progress if possible
        try:
            if self.checkpoint_manager.is_enabled():
                self.logger.log_info("Saving checkpoint at current position")
                await self.checkpoint_manager.save_checkpoint(
                    self.tracker.current_phase_index,
                    self.tracker.current_step_index,
                    self.variables.get_all()
                )
        except Exception as e:
            self.logger.log_warning(f"Error saving checkpoint during cleanup: {str(e)}")
        
        # Clean up resources
        try:
            self.session_manager.clear_temp_sessions()
        except Exception as e:
            self.logger.log_warning(f"Error cleaning up sessions: {str(e)}")
            
        # Finalize metrics
        try:
            self.observer_manager.notify(PlaybookEndEvent())
            self.observer_manager.cleanup()
        except Exception as e:
            self.logger.log_warning(f"Error cleaning up metrics: {str(e)}")
            
        self.tracker.mark_cleanup_done()
        self.logger.log_info("Playbook cleanup complete")

    async def execute(self) -> None:
        """
        Execute the playbook.
        
        Raises:
            ValueError: If the session does not exist
            aiohttp.ClientError: If any request fails
        """
        # Start metrics collection for the playbook
        self.observer_manager.notify(PlaybookStartEvent())
        
        try:
            # Check for checkpoint if incremental is enabled
            checkpoint = await self.checkpoint_manager.load_checkpoint()
            
            # Initialize temporary sessions if configured
            self.session_manager.initialize_temp_sessions(self.config.sessions)

            # Set variables from checkpoint if available
            if checkpoint and checkpoint.variables:
                self.variables.set_all(checkpoint.variables)
            # Execute phases
            for phase_index, phase_config in enumerate(self.config.phases):
                self.tracker.current_phase_index = phase_index
                self.tracker.current_step_index = 0
                
                phase = PhaseContext(phase_index, phase_config)
                # Skip phases before checkpoint
                if self.checkpoint_manager.should_skip_phase(phase_index, checkpoint):
                    self.logger.log_info(f"Skipping phase {phase_index}: {phase.name} (already completed)")
                    continue
                self.logger.log_info(f"Executing phase {phase.index}: {phase.name}")
                
                # Start metrics collection for the phase
                self.observer_manager.notify(PhaseStartEvent(phase))
                
                try:
                    if phase.parallel:
                        # For parallel execution, we need to handle checkpoints differently
                        if self.checkpoint_manager.should_restart_parallel_phase(phase_index, checkpoint):
                            # This is the phase where we left off - we need to re-run it completely
                            # since we can't guarantee which steps completed in parallel execution
                            self.logger.log_info("Restarting parallel phase from beginning")
                            checkpoint = None
                        
                        # Execute steps in parallel
                        tasks = [
                            self._execute_step(step, phase, step_index)
                            for step_index, step in enumerate(phase.steps)
                        ]
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Process results and log errors
                        for step_index, result in enumerate(results):
                            if isinstance(result, BaseException):
                                self.logger.log_error(f"Step {step_index} failed: {str(result)}")
                        
                        # Save checkpoint after parallel phase
                        await self.checkpoint_manager.save_checkpoint(
                            phase_index, 
                            len(phase.steps) - 1,
                            self.variables.get_all()
                        )
                    else:
                        # Execute steps sequentially
                        for step_index, step in enumerate(phase.steps):
                            self.tracker.current_step_index = step_index
                            
                            # Skip steps before checkpoint in the current phase
                            if self.checkpoint_manager.should_skip_step(phase.index, step_index, checkpoint):
                                self.logger.log_info(f"Skipping step {step_index} (already completed)")
                                continue
                                
                            await self._execute_step(step, phase, step_index)
                            
                            # Save checkpoint after each step
                            await self.checkpoint_manager.save_checkpoint(
                                phase_index, 
                                step_index,
                                self.variables.get_all()
                            )
                    
                    # End metrics collection for the phase
                    self.observer_manager.notify(PhaseEndEvent(phase))
                except asyncio.CancelledError:
                    self.logger.log_warning(f"Phase {phase.name} execution was cancelled")
                    # End phase metrics in case of cancellation
                    self.observer_manager.notify(PhaseEndEvent(phase))
                    raise
            self.observer_manager.notify(PlaybookEndEvent())
            # Clear checkpoint after successful execution
            await self.checkpoint_manager.clear_checkpoint()
        except asyncio.CancelledError:
            self.logger.log_info("Playbook execution was cancelled")
            await self.cancel_and_cleanup()
        except Exception as e:
            self.logger.log_error(str(e))
            await self.cancel_and_cleanup()
        finally:
            # Always ensure cleanup happens
            if not self.tracker.cleanup_done:
                self.session_manager.clear_temp_sessions()
                self.observer_manager.cleanup()
                self.logger.log_debug("Playbook cleanup complete")

    async def _execute_step(self, step_config: StepConfig, phase: PhaseContext, step_index: int) -> None:
        """
        Execute a single step of the playbook.
        
        Args:
            step_config: The step configuration to execute
            phase: The context for the phase
            step_index: Index of the step in the phase
        """
        session = self.session_manager.get_session(step_config.session)
        step = StepContext(phase.id, step_index, step_config, session)
        
        # Start metrics collection for the step
        self.observer_manager.notify(StepStartEvent(step))
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
                    rendered_step = step.config.model_copy(deep=True)
                    rendered_step.request = self.config_renderer.render_request_config(step.request, context)
                    if step.store:
                        rendered_step.store = [self.config_renderer.render_store_config(store, context) for store in step.store]
                    else:
                        rendered_step.store = None
                    
                    
                    # Add task for this iteration
                    tasks.append(self._execute_single_step(step, rendered_step))

                # Execute iterations based on parallel flag
                if step.parallel:
                    self.logger.log_info(f"Executing {len(tasks)} iterations in parallel")
                    await asyncio.gather(*tasks, return_exceptions=True)
                else:
                    self.logger.log_info(f"Executing {len(tasks)} iterations sequentially")
                    for task in tasks:
                        await task
            else:
                context = {
                    **self.variables.get_all(),
                }
                rendered_step = step.config.model_copy(deep=True)
                rendered_step.request = self.config_renderer.render_request_config(step.request, context)
                if step.store:
                    rendered_step.store = [self.config_renderer.render_store_config(store, context) for store in step.store]
                else:
                    rendered_step.store = None
                step.config = rendered_step
                # Execute step directly if no iteration is configured
                await self._execute_single_step(step)

        except asyncio.CancelledError:
            self.logger.log_warning(f"Step {step_index} in phase {phase.name} was cancelled")
            # End step metrics in case of cancellation 
            try:
                self.observer_manager.notify(StepEndEvent(step))
            except Exception:
                pass
            raise
        except Exception as e:
            if step.on_error == "ignore":
                self.logger.log_warning(f"Step failed but continuing: {str(e)}")
            else:
                raise
        
        # End metrics collection for the step
        self.observer_manager.notify(StepEndEvent(step))

    async def _execute_single_step(self, context: StepContext, override_config: StepConfig | None = None) -> None:
        """
        Execute a single step without iteration.
        
        Args:
            context: The step context
            override_config: Optional override configuration for iterations
        """
        # Get session for this step
        session = context.session
        step = override_config if override_config else context.config

        # Create client using factory
        client = self.client_factory.create_client(session, step)
        request_context = RequestContext(step_id=context.id, config=step.request)
        
        # Start metrics collection for the request
        self.observer_manager.notify(RequestStartEvent(request_context))
        
        # Create task and track it for graceful shutdown
        task = asyncio.create_task(client.execute_request(HttpRequestSpec(
            url=step.request.endpoint,
            method=step.request.method.value,
            headers=step.request.headers,
            data=step.request.data,
            params=step.request.params
        )))
        self._running_requests.append(task)
        
        try:
            self.logger.log_info(f"Executing request: {step.request.endpoint}")
            # Execute request
            response = await task
            
            # Remove from tracking once complete
            if task in self._running_requests:
                self._running_requests.remove(task)

            # Log response
            self.logger.log_status(response.status)
            try:
                body = await response.json()
                body_str = json.dumps(body, indent=2)
                
                # Store response data if configured
                if step.store:
                    try:
                        store_vars = await self.variables.store_response_data(step.store, body)
                        context.store_results.append(store_vars)
                    except Exception as e:
                        if step.on_error != "ignore":
                            raise
                
            except json.JSONDecodeError:
                body_str = await response.text()
            self.logger.log_body(body_str)

        except asyncio.CancelledError:
            self.logger.log_warning(f"Request was cancelled")
            # Clean up the tracking
            if task in self._running_requests:
                self._running_requests.remove(task)
            raise
        except Exception as e:
            # Clean up the tracking
            if task in self._running_requests:
                self._running_requests.remove(task)
                
            if step.on_error != "ignore":
                raise
        finally:
            # Ensure executor is closed
            await client.close()
            
            # Get request metadata and end metrics collection
            metadata = client.get_last_request_execution_metadata()
            if metadata:
                self.observer_manager.notify(RequestEndEvent(request_context, metadata))