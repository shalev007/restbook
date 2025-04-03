import json
import hashlib
import os
from typing import Dict, Any, Optional, List, Union
import asyncio
import jq  # type: ignore
from datetime import datetime

from src.modules.session.session import Session

from .config import (
    AuthType, PlaybookConfig, PhaseConfig, StepConfig, StoreConfig, 
    RequestConfig, SessionConfig, AuthConfig, AuthCredentials, RetryConfig
)
from .validator import PlaybookYamlValidator
from .template import TemplateRenderer
from .checkpoint import CheckpointStore, CheckpointData, create_checkpoint_store
from .variables import VariableManager
from ..session.session_store import SessionStore
from ..logging import BaseLogger
from ..request.resilient_http_client import RequestParams, ResilientHttpClient, ResilientHttpClientConfig
from ..request.circuit_breaker import CircuitBreaker
from ..metrics import (
    MetricsCollector, RequestMetrics, StepMetrics, PhaseMetrics, PlaybookMetrics,
    create_metrics_collector
)

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
            
        # Initialize metrics collector if enabled
        self.metrics_collector: Optional[MetricsCollector] = None
        if self.config.metrics and self.config.metrics.enabled:
            self.metrics_collector = create_metrics_collector(self.config.metrics)
            logger.log_info(f"Metrics collection enabled with collector type: {self.config.metrics.collector}")

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
        
        # Handle loading data from file if specified
        data = None
        if request.fromFile:
            # Render the file path with variables/templates
            file_path = self.renderer.render_template(request.fromFile, context)
            
            # Support both absolute paths and paths relative to the working directory
            if not os.path.isabs(file_path):
                file_path = os.path.join(os.getcwd(), file_path)
                
            try:
                # Read and parse the JSON file
                with open(file_path, 'r') as f:
                    file_content = f.read()
                    
                # Parse the file content as JSON
                data = json.loads(file_content)
                
                # Render templates in the loaded data
                data = self.renderer.render_dict(data, context)
                self.logger.log_info(f"Loaded request data from file: {file_path}")
            except FileNotFoundError:
                raise ValueError(f"Request data file not found: {file_path}")
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON in request data file: {file_path}")
            except Exception as e:
                raise ValueError(f"Error loading request data from file {file_path}: {str(e)}")
        else:
            # Use inline data if specified
            data = self.renderer.render_dict(request.data, context) if request.data else None
        
        rendered_data: Dict[str, Union[str, Optional[Dict[str, Any]]]] = {
            "method": request.method,
            "endpoint": self.renderer.render_template(request.endpoint, context),
            "data": data,
            "params": self.renderer.render_dict(request.params, context) if request.params else None,
            "headers": self.renderer.render_dict(request.headers, context) if request.headers else None,
            # Don't include fromFile in the rendered config
            "fromFile": None
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
        playbook_start_time = datetime.now()
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        phases_metrics = []
        
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
                
                phase_start_time = datetime.now()
                phase_steps_metrics = []
                
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
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results for metrics
                    for step_index, result in enumerate(results):
                        if isinstance(result, BaseException):
                            failed_requests += 1
                            self.logger.log_error(f"Step {step_index} failed: {str(result)}")
                        else:
                            step_metrics, req_count, success_count, fail_count = result
                            phase_steps_metrics.append(step_metrics)
                            total_requests += req_count
                            successful_requests += success_count
                            failed_requests += fail_count
                    
                    # Save checkpoint after parallel phase
                    await self._save_checkpoint(phase_index, len(phase.steps) - 1)
                else:
                    # Execute steps sequentially
                    for step_index, step in enumerate(phase.steps):
                        # Skip steps before checkpoint in the current phase
                        if checkpoint and phase_index == checkpoint.current_phase and step_index <= checkpoint.current_step:
                            self.logger.log_info(f"Skipping step {step_index} (already completed)")
                            continue
                            
                        result = await self._execute_step(step, session_store)
                        step_metrics, req_count, success_count, fail_count = result
                        phase_steps_metrics.append(step_metrics)
                        total_requests += req_count
                        successful_requests += success_count
                        failed_requests += fail_count
                        
                        # Save checkpoint after each step
                        await self._save_checkpoint(phase_index, step_index)
                
                # Record phase metrics
                phase_end_time = datetime.now()
                phase_duration_ms = (phase_end_time - phase_start_time).total_seconds() * 1000
                phase_metrics = PhaseMetrics(
                    name=phase.name,
                    start_time=phase_start_time,
                    end_time=phase_end_time,
                    duration_ms=phase_duration_ms,
                    steps=phase_steps_metrics,
                    parallel=bool(phase.parallel)  # Convert to bool to satisfy type hint
                )
                phases_metrics.append(phase_metrics)
                
                if self.metrics_collector:
                    self.metrics_collector.record_phase(phase_metrics)
            
            # Clear checkpoint after successful execution
            await self._clear_checkpoint()
            
        except Exception as e:
            self.logger.log_error(str(e))
            raise
        finally:
            # Clean up temporary sessions
            self._temp_sessions.clear()
            
            # Record playbook metrics
            if self.metrics_collector:
                playbook_end_time = datetime.now()
                playbook_duration_ms = (playbook_end_time - playbook_start_time).total_seconds() * 1000
                playbook_metrics = PlaybookMetrics(
                    start_time=playbook_start_time,
                    end_time=playbook_end_time,
                    duration_ms=playbook_duration_ms,
                    phases=phases_metrics,
                    total_requests=total_requests,
                    successful_requests=successful_requests,
                    failed_requests=failed_requests,
                    total_duration_ms=playbook_duration_ms
                )
                self.metrics_collector.record_playbook(playbook_metrics)
                self.metrics_collector.finalize()

    async def _execute_phase(self, phase: PhaseConfig, session_store: SessionStore) -> None:
        """Execute a single phase of the playbook."""
        phase_start_time = datetime.now()
        phase_steps_metrics = []
        
        if phase.parallel:
            # Execute steps in parallel
            tasks = [
                self._execute_step(step, session_store)
                for step in phase.steps
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results for metrics
            for result in results:
                if isinstance(result, BaseException):
                    self.logger.log_error(f"Step failed: {str(result)}")
                else:
                    step_metrics, _, _, _ = result
                    phase_steps_metrics.append(step_metrics)
        else:
            # Execute steps sequentially
            for step in phase.steps:
                result = await self._execute_step(step, session_store)
                step_metrics, _, _, _ = result
                phase_steps_metrics.append(step_metrics)
        
        # Record phase metrics
        phase_end_time = datetime.now()
        phase_duration_ms = (phase_end_time - phase_start_time).total_seconds() * 1000
        phase_metrics = PhaseMetrics(
            name=phase.name,
            start_time=phase_start_time,
            end_time=phase_end_time,
            duration_ms=phase_duration_ms,
            steps=phase_steps_metrics,
            parallel=bool(phase.parallel)  # Convert to bool to satisfy type hint
        )
        
        if self.metrics_collector:
            self.metrics_collector.record_phase(phase_metrics)

    async def _execute_step(self, step: StepConfig, session_store: SessionStore) -> tuple[StepMetrics, int, int, int]:
        """
        Execute a single step of the playbook.
        
        Returns:
            Tuple containing:
            - StepMetrics: Metrics for the step
            - int: Total number of requests
            - int: Number of successful requests
            - int: Number of failed requests
        """
        step_start_time = datetime.now()
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        request_metrics_list: List[RequestMetrics] = []
        
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
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results for metrics
                    for result in results:
                        if isinstance(result, BaseException):
                            failed_requests += 1
                            self.logger.log_error(f"Iteration failed: {str(result)}")
                        else:
                            req_metrics, req_count, success_count, fail_count = result
                            request_metrics_list.append(req_metrics)
                            total_requests += req_count
                            successful_requests += success_count
                            failed_requests += fail_count
                else:
                    self.logger.log_info(f"Executing {len(tasks)} iterations sequentially")
                    for task in tasks:
                        result = await task
                        req_metrics, req_count, success_count, fail_count = result
                        request_metrics_list.append(req_metrics)
                        total_requests += req_count
                        successful_requests += success_count
                        failed_requests += fail_count
            else:
                context = {
                    **self.variables.get_all(),
                }
                rendered_step = step.model_copy(deep=True)
                rendered_step.request = self._render_request_config(step.request, context)
                if step.store:
                    rendered_step.store = [self._render_store_config(store, context) for store in step.store]
                else:
                    rendered_step.store = None
                # Execute step directly if no iteration is configured
                result = await self._execute_single_step(rendered_step, session_store)
                req_metrics, req_count, success_count, fail_count = result
                request_metrics_list.append(req_metrics)
                total_requests += req_count
                successful_requests += success_count
                failed_requests += fail_count

        except Exception as e:
            if step.on_error == "ignore":
                self.logger.log_info(f"Step failed but continuing: {str(e)}")
                failed_requests += 1
            else:
                raise
        
        # Create step metrics
        step_end_time = datetime.now()
        step_duration_ms = (step_end_time - step_start_time).total_seconds() * 1000
        step_metrics = StepMetrics(
            session=step.session,
            request=request_metrics_list[0] if request_metrics_list else RequestMetrics(
                method=step.request.method.value,
                endpoint=step.request.endpoint,
                start_time=step_start_time,
                end_time=step_end_time,
                status_code=0,
                duration_ms=step_duration_ms,
                success=False,
                error="No requests executed"
            ),
            retry_count=0,  # This would need to be tracked in the request execution
            store_vars=[store.var for store in (step.store or [])]
        )
        
        if self.metrics_collector:
            self.metrics_collector.record_step(step_metrics)
        
        return step_metrics, total_requests, successful_requests, failed_requests

    async def _execute_single_step(self, step: StepConfig, session_store: SessionStore) -> tuple[RequestMetrics, int, int, int]:
        """
        Execute a single step without iteration.
        
        Returns:
            Tuple containing:
            - RequestMetrics: Metrics for the request
            - int: Total number of requests (always 1 for this method)
            - int: Number of successful requests
            - int: Number of failed requests
        """
        # Get session for this step
        if step.session in self._temp_sessions:
            session = self._temp_sessions[step.session]
        else:
            session = session_store.get_session(step.session)

        # Merge session and step configurations
        # Start with session's retry config as base, or default values
        base_retry = RetryConfig(
            max_retries=session.retry_config.max_retries if session.retry_config else 2,
            backoff_factor=session.retry_config.backoff_factor if session.retry_config else 1.0,
            max_delay=session.retry_config.max_delay if session.retry_config else None
        )
        
        # Override with step's retry config if provided
        retry_config = RetryConfig(
            max_retries=step.retry.max_retries if step.retry else base_retry.max_retries,
            backoff_factor=step.retry.backoff_factor if step.retry else base_retry.backoff_factor,
            max_delay=step.retry.max_delay if step.retry else base_retry.max_delay
        )
        
        validate_ssl = step.validate_ssl if step.validate_ssl is not None else (session.validate_ssl if session.validate_ssl is not None else True)
        timeout = step.timeout if step.timeout is not None else (session.timeout if session.timeout is not None else 30)
        
        # Use step's circuit breaker config if provided, otherwise use session's circuit breaker
        circuit_breaker = None
        if step.retry and step.retry.circuit_breaker:
            circuit_breaker = CircuitBreaker(
                threshold=step.retry.circuit_breaker.threshold,
                reset_timeout=step.retry.circuit_breaker.reset,
                jitter=step.retry.circuit_breaker.jitter
            )
        elif session.circuit_breaker:
            circuit_breaker = session.circuit_breaker
        
        execution_config = ResilientHttpClientConfig(
            timeout=timeout,
            verify_ssl=validate_ssl,
            max_retries=retry_config.max_retries,
            backoff_factor=retry_config.backoff_factor,
            max_delay=retry_config.max_delay,
            use_server_retry_delay=retry_config.rate_limit.use_server_retry_delay,
            retry_header=retry_config.rate_limit.retry_header
        )

        # Convert playbook request config to executor request config
        request_config = self._convert_to_executor_config(step.request)

        # Create request executor with step-specific config
        client = ResilientHttpClient(
            session=session,
            config=execution_config,
            logger=self.logger,
            circuit_breaker=circuit_breaker
        )

        request_start_time = datetime.now()
        success = False
        error = None
        status_code = 0
        
        try:
            # Execute request
            response = await client.execute_request(request_config)
            status_code = response.status
            success = 200 <= status_code < 300

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
        except Exception as e:
            error = str(e)
            if step.on_error != "ignore":
                raise
        finally:
            # Ensure executor is closed
            await client.close()
            
            # Create request metrics
            request_end_time = datetime.now()
            duration_ms = (request_end_time - request_start_time).total_seconds() * 1000
            request_metrics = RequestMetrics(
                method=step.request.method.value,
                endpoint=step.request.endpoint,
                start_time=request_start_time,
                end_time=request_end_time,
                status_code=status_code,
                duration_ms=duration_ms,
                success=success,
                error=error
            )
            
            if self.metrics_collector:
                self.metrics_collector.record_request(request_metrics)
            
            return request_metrics, 1, 1 if success else 0, 0 if success else 1

    def _convert_to_executor_config(self, playbook_config: RequestConfig) -> RequestParams:
        """Convert a playbook request config to an executor request config.
        
        Args:
            playbook_config: The playbook's request configuration
            
        Returns:
            RequestParams: The executor's request configuration
        """
        
        return RequestParams(
            url=playbook_config.endpoint,
            method=playbook_config.method.value,
            headers=playbook_config.headers,
            data=playbook_config.data,
            params=playbook_config.params
        )