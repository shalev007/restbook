"""Tests for the shutdown coordinator module."""

import asyncio
import pytest
from unittest.mock import Mock

from src.modules.shutdown.coordinator import ShutdownCoordinator

@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = Mock()
    logger.log_info = Mock()
    logger.log_error = Mock()
    logger.log_warning = Mock()
    return logger

@pytest.mark.asyncio
async def test_shutdown_coordinator(mock_logger):
    """Test basic shutdown coordinator functionality."""
    coordinator = ShutdownCoordinator(mock_logger)
    
    # Track execution order
    execution_order = []
    
    # Register handlers with different priorities
    coordinator.register_handler(
        "high_priority",
        lambda: execution_order.append("high"),
        priority=0
    )
    coordinator.register_handler(
        "medium_priority",
        lambda: execution_order.append("medium"),
        priority=1
    )
    coordinator.register_handler(
        "low_priority",
        lambda: execution_order.append("low"),
        priority=2
    )
    
    # Start shutdown
    await coordinator.shutdown()
    
    # Verify execution order
    assert execution_order == ["high", "medium", "low"]
    assert coordinator.is_shutting_down is True
    
    # Verify logging
    mock_logger.log_info.assert_any_call("Starting graceful shutdown...")
    mock_logger.log_info.assert_any_call("Executing shutdown handler: high_priority")
    mock_logger.log_info.assert_any_call("Executing shutdown handler: medium_priority")
    mock_logger.log_info.assert_any_call("Executing shutdown handler: low_priority")
    mock_logger.log_info.assert_any_call("Graceful shutdown completed")

@pytest.mark.asyncio
async def test_shutdown_event(mock_logger):
    """Test shutdown event signaling."""
    coordinator = ShutdownCoordinator(mock_logger)
    
    async def wait_for_shutdown():
        await coordinator.wait_for_shutdown()
        return True
    
    # Start waiting for shutdown
    task = asyncio.create_task(wait_for_shutdown())
    
    # Verify task is waiting
    await asyncio.sleep(0.1)
    assert not task.done()
    
    # Trigger shutdown
    await coordinator.shutdown()
    
    # Verify task completed
    assert await task is True

@pytest.mark.asyncio
async def test_double_shutdown(mock_logger):
    """Test that shutdown can only be executed once."""
    coordinator = ShutdownCoordinator(mock_logger)
    
    execution_count = 0
    def increment_count():
        nonlocal execution_count
        execution_count += 1
    
    coordinator.register_handler(
        "test_handler",
        increment_count
    )
    
    # Execute shutdown twice
    await coordinator.shutdown()
    await coordinator.shutdown()
    
    # Verify handler only executed once
    assert execution_count == 1
    assert mock_logger.log_info.call_count == 3  # Start, handler, complete

@pytest.mark.asyncio
async def test_error_handling(mock_logger):
    """Test error handling in shutdown handlers."""
    coordinator = ShutdownCoordinator(mock_logger)
    
    def raise_error():
        raise ValueError("Test error")
    
    coordinator.register_handler(
        "error_handler",
        raise_error
    )
    
    # Execute shutdown
    await coordinator.shutdown()
    
    # Verify error was logged
    mock_logger.log_error.assert_called_once_with("Error in shutdown handler error_handler: Test error")

@pytest.mark.asyncio
async def test_shutdown_timeout(mock_logger):
    """Test shutdown timeout functionality."""
    coordinator = ShutdownCoordinator(mock_logger, shutdown_timeout=0.1)
    
    async def slow_handler():
        await asyncio.sleep(0.2)  # Longer than timeout
    
    coordinator.register_handler(
        "slow_handler",
        slow_handler
    )
    
    # Execute shutdown
    start_time = asyncio.get_event_loop().time()
    await coordinator.shutdown()
    end_time = asyncio.get_event_loop().time()
    
    # Verify timeout occurred
    assert end_time - start_time < 0.2  # Should timeout before handler completes
    mock_logger.log_warning.assert_called_once_with(
        "Shutdown timed out after 0.1 seconds. Some handlers may not have completed gracefully."
    )

@pytest.mark.asyncio
async def test_async_handlers_completion(mock_logger):
    """Test that async handlers complete within timeout."""
    coordinator = ShutdownCoordinator(mock_logger, shutdown_timeout=0.2)
    
    async def fast_handler():
        await asyncio.sleep(0.1)  # Shorter than timeout
    
    coordinator.register_handler(
        "fast_handler",
        fast_handler
    )
    
    # Execute shutdown
    start_time = asyncio.get_event_loop().time()
    await coordinator.shutdown()
    end_time = asyncio.get_event_loop().time()
    
    # Verify handler completed within timeout
    assert end_time - start_time >= 0.1  # Handler should have completed
    assert end_time - start_time < 0.2  # But before timeout
    mock_logger.log_warning.assert_not_called()  # No timeout warning 