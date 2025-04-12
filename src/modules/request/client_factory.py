from typing import Optional
from ..logging import BaseLogger
from .resilient_http_client import ResilientHttpClient, ResilientHttpClientConfig
from .circuit_breaker import CircuitBreaker
from ..playbook.config import StepConfig, RetryConfig, RequestConfig
from ..session.session import Session

class ResilientHttpClientFactory:
    """Factory for creating ResilientHttpClient instances with proper configuration."""
    
    def __init__(self, logger: BaseLogger):
        """Initialize the factory.
        
        Args:
            logger: Logger instance for request/response logging
        """
        self.logger = logger

    def _create_retry_config(self, session: Session, step: StepConfig) -> RetryConfig:
        """Create retry configuration by merging session and step settings.
        
        Args:
            session: The session containing base retry settings
            step: The step configuration containing potential overrides
            
        Returns:
            RetryConfig: The merged retry configuration
        """
        # Start with session's retry config as base, or default values
        base_retry = RetryConfig(
            max_retries=session.retry_config.max_retries if session.retry_config else 2,
            backoff_factor=session.retry_config.backoff_factor if session.retry_config else 1.0,
            max_delay=session.retry_config.max_delay if session.retry_config else None
        )
        
        # Override with step's retry config if provided
        return RetryConfig(
            max_retries=step.retry.max_retries if step.retry else base_retry.max_retries,
            backoff_factor=step.retry.backoff_factor if step.retry else base_retry.backoff_factor,
            max_delay=step.retry.max_delay if step.retry else base_retry.max_delay
        )

    def _create_circuit_breaker(self, session: Session, step: StepConfig) -> Optional[CircuitBreaker]:
        """Create circuit breaker configuration based on session and step settings.
        
        Args:
            session: The session containing base circuit breaker settings
            step: The step configuration containing potential overrides
            
        Returns:
            Optional[CircuitBreaker]: The circuit breaker configuration, if any
        """
        if step.retry and step.retry.circuit_breaker:
            return CircuitBreaker(
                threshold=step.retry.circuit_breaker.threshold,
                reset_timeout=step.retry.circuit_breaker.reset,
                jitter=step.retry.circuit_breaker.jitter
            )
        return session.circuit_breaker

    def create_client(self, session: Session, step: StepConfig) -> ResilientHttpClient:
        """Create a new ResilientHttpClient with proper configuration.
        
        Args:
            session: The session to use for the client
            step: The step configuration containing request settings
            
        Returns:
            ResilientHttpClient: A configured HTTP client
        """
        retry_config = self._create_retry_config(session, step)
        circuit_breaker = self._create_circuit_breaker(session, step)
        
        # Merge session and step configurations for SSL and timeout
        validate_ssl = step.validate_ssl if step.validate_ssl is not None else (session.validate_ssl if session.validate_ssl is not None else True)
        timeout = step.timeout if step.timeout is not None else (session.timeout if session.timeout is not None else 30)
        
        execution_config = ResilientHttpClientConfig(
            timeout=timeout,
            verify_ssl=validate_ssl,
            max_retries=retry_config.max_retries,
            backoff_factor=retry_config.backoff_factor,
            max_delay=retry_config.max_delay,
            use_server_retry_delay=retry_config.rate_limit.use_server_retry_delay if step.retry and step.retry.rate_limit else False,
            retry_header=retry_config.rate_limit.retry_header if step.retry and step.retry.rate_limit and retry_config.rate_limit.retry_header else ""
        )

        return ResilientHttpClient(
            session=session,
            config=execution_config,
            logger=self.logger,
            circuit_breaker=circuit_breaker
        ) 