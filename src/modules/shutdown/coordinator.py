"""Shutdown coordinator for managing graceful shutdown of application components."""

import asyncio
import signal
from dataclasses import dataclass
from typing import Callable, List, Optional

from ..logging import BaseLogger

@dataclass
class ShutdownHandler:
    """Handler for shutdown operations."""
    name: str
    handler: Callable
    priority: int = 0

class ShutdownCoordinator:
    """Coordinates graceful shutdown of application components."""
    
    def __init__(self, logger: BaseLogger, shutdown_timeout: float = 5.0):
        """
        Initialize the shutdown coordinator.
        
        Args:
            logger: Logger instance for logging shutdown events
            shutdown_timeout: Timeout in seconds to wait for graceful shutdown
        """
        self._handlers: List[ShutdownHandler] = []
        self._shutdown_event = asyncio.Event()
        self._is_shutting_down = False
        self._shutdown_lock = asyncio.Lock()
        self.logger = logger
        self.shutdown_timeout = shutdown_timeout
        
        # Register signal handlers
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        # Get the event loop
        loop = asyncio.get_event_loop()
        
        # Register handlers for common termination signals
        for sig in (signal.SIGTERM, signal.SIGINT):
            def signal_handler() -> None:
                asyncio.create_task(self._handle_signal(sig))
            
            loop.add_signal_handler(sig, signal_handler)
    
    async def _handle_signal(self, signum: int) -> None:
        """Handle termination signals.
        
        Args:
            signum: The signal number that was received
        """
        signal_name = signal.Signals(signum).name
        self.logger.log_info(f"Received {signal_name} signal, initiating graceful shutdown...")
        await self.shutdown()
    
    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._is_shutting_down
    
    def register_handler(self, name: str, handler: Callable, priority: int = 0) -> None:
        """Register a shutdown handler.
        
        Args:
            name: Name of the handler
            handler: Callable to execute during shutdown
            priority: Priority of the handler (lower numbers execute first)
        """
        self._handlers.append(ShutdownHandler(name, handler, priority))
        # Sort handlers by priority
        self._handlers.sort(key=lambda h: h.priority)
    
    async def shutdown(self) -> None:
        """Execute all registered shutdown handlers in order of priority."""
        async with self._shutdown_lock:
            if self._is_shutting_down:
                return
            
            self._is_shutting_down = True
            self._shutdown_event.set()
            
            self.logger.log_info("Starting graceful shutdown...")
            
            # Create tasks for all handlers
            tasks = []
            for handler in self._handlers:
                try:
                    self.logger.log_info(f"Executing shutdown handler: {handler.name}")
                    if asyncio.iscoroutinefunction(handler.handler):
                        tasks.append(asyncio.create_task(handler.handler()))
                    else:
                        handler.handler()
                except Exception as e:
                    self.logger.log_error(f"Error in shutdown handler {handler.name}: {str(e)}")
            
            # Wait for all async handlers to complete with timeout
            if tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=self.shutdown_timeout
                    )
                except asyncio.TimeoutError:
                    self.logger.log_warning(
                        f"Shutdown timed out after {self.shutdown_timeout} seconds. "
                        "Some handlers may not have completed gracefully."
                    )
            
            self.logger.log_info("Graceful shutdown completed")
    
    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown to be initiated."""
        await self._shutdown_event.wait() 