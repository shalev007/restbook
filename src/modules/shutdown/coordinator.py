"""Shutdown coordinator for managing graceful shutdown of application components."""

import asyncio
from asyncio import AbstractEventLoop, Task
import signal
from dataclasses import dataclass
from typing import Callable, List, Optional, TypeVar, Any, Coroutine, cast, Generic, Dict, Union, Tuple
import types

from ..logging import BaseLogger

# Define a bound type variable
T = TypeVar('T')

# Type for signal handlers
SignalHandlerType = Union[Callable[[int, Optional[types.FrameType]], Any], int, None]

@dataclass
class ShutdownHandler:
    """Handler for shutdown operations."""
    name: str
    handler: Callable
    priority: int = 0

class ShutdownCoordinator(Generic[T]):
    """Coordinates graceful shutdown of application components."""
    
    def __init__(self, logger: BaseLogger, shutdown_timeout: float = 5.0):
        """
        Initialize the shutdown coordinator.
        
        Args:
            logger: Logger instance for logging shutdown events
            shutdown_timeout: Timeout in seconds to wait for graceful shutdown
        """
        self._handlers: List[ShutdownHandler] = []
        self._is_shutting_down = False
        self.logger = logger
        self.shutdown_timeout = shutdown_timeout
        self._main_task: Optional[Task[T]] = None
        self._active_loop: Optional[AbstractEventLoop] = None
        self._original_sigint: SignalHandlerType = None
        self._original_sigterm: SignalHandlerType = None
    
    def setup_signal_handlers(self) -> None:
        """
        Setup signal handlers for the current event loop.
        This should be called from the main thread.
        """
        # Store original signal handlers to restore later
        self._original_sigint = signal.getsignal(signal.SIGINT)
        self._original_sigterm = signal.getsignal(signal.SIGTERM)
        
        # Register handler for both signals
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        if self._original_sigint:
            signal.signal(signal.SIGINT, self._original_sigint)
        if self._original_sigterm:
            signal.signal(signal.SIGTERM, self._original_sigterm)
    
    def _handle_signal(self, sig_num: int, frame: Optional[types.FrameType]) -> None:
        """
        Handle termination signals. This is a synchronous method
        that will be called directly by the signal handler.
        
        Args:
            sig_num: The signal number that was received
            frame: The current stack frame
        """
        try:
            sig_name = signal.Signals(sig_num).name
            print(f"\nReceived {sig_name} signal, initiating graceful shutdown...")
            
            # Cancel the main task if it's running
            if self._main_task and not self._main_task.done() and self._active_loop:
                # Schedule the task cancellation
                self._active_loop.call_soon_threadsafe(self._main_task.cancel)
            
        except Exception as e:
            print(f"Error handling signal: {e}")
    
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
        # Check if handler with this name already exists
        for existing in self._handlers:
            if existing.name == name:
                # Replace with new handler
                existing.handler = handler
                existing.priority = priority
                # Re-sort handlers by priority
                self._handlers.sort(key=lambda h: h.priority)
                return
                
        self._handlers.append(ShutdownHandler(name, handler, priority))
        # Sort handlers by priority
        self._handlers.sort(key=lambda h: h.priority)
    
    async def execute_handlers(self) -> None:
        """
        Execute all registered shutdown handlers in order of priority.
        This is separated from the shutdown logic to allow it to be
        called directly in the event loop.
        """
        if self._is_shutting_down:
            return
            
        self._is_shutting_down = True
        self.logger.log_info("Starting graceful shutdown...")
        
        # Create tasks for all handlers
        tasks = []
        for handler in self._handlers:
            try:
                self.logger.log_info(f"Executing shutdown handler: {handler.name}")
                if asyncio.iscoroutinefunction(handler.handler):
                    tasks.append(asyncio.create_task(handler.handler()))
                else:
                    result = handler.handler()
                    # If handler returns a coroutine, add it to tasks
                    if asyncio.iscoroutine(result):
                        tasks.append(asyncio.create_task(result))
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
    
    def run_async_with_signals(self, coroutine: Coroutine[Any, Any, T]) -> T:
        """
        Run an async coroutine with proper signal handling and graceful shutdown.
        
        This method creates a new event loop, sets up signal handlers, and runs
        the provided coroutine. When a signal is received, it will cancel the
        coroutine and perform graceful shutdown.
        
        Args:
            coroutine: The coroutine to execute
            
        Returns:
            The result of the coroutine
            
        Raises:
            Any exception raised by the coroutine
        """
        result = None
        
        # Create and set up a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._active_loop = loop
        
        # Set up signal handlers
        self.setup_signal_handlers()
        
        try:
            # Create task and store reference for potential cancellation
            main_task = loop.create_task(coroutine)
            self._main_task = cast(Task[T], main_task)  # Safe cast since we know the type
            
            try:
                result = loop.run_until_complete(main_task)
            except asyncio.CancelledError:
                self.logger.log_info("Task was cancelled, performing graceful shutdown")
                # Execute handlers when cancelled
                loop.run_until_complete(self.execute_handlers())
            
        except Exception as e:
            self.logger.log_error(f"Error during execution: {str(e)}")
            
            # Still attempt cleanup on error
            try:
                loop.run_until_complete(self.execute_handlers())
            except Exception as cleanup_err:
                self.logger.log_error(f"Error during cleanup: {str(cleanup_err)}")
            
            # Re-raise the original exception
            raise
            
        finally:
            # Reset references
            self._main_task = None
            self._active_loop = None
            
            # Restore original signal handlers
            self.restore_signal_handlers()
            
            # Clean up any pending tasks
            try:
                pending = asyncio.all_tasks(loop)
                if pending:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception as e:
                self.logger.log_warning(f"Error cleaning up pending tasks: {str(e)}")
                
            # Close the loop properly
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
            except Exception as e:
                self.logger.log_warning(f"Error closing event loop: {str(e)}")
        
        if result is None and not self._is_shutting_down:
            raise RuntimeError("Task was cancelled before completion")
            
        return cast(T, result) 