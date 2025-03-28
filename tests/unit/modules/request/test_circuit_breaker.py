import pytest
from datetime import datetime, timedelta, UTC
from src.modules.request.circuit_breaker import CircuitBreaker

class TestCircuitBreaker:
    """Test cases for CircuitBreaker class."""

    def test_init(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(threshold=2, reset_timeout=10, jitter=0.1)
        assert cb.threshold == 2
        assert cb.reset_timeout == 10
        assert cb.jitter == 0.1
        assert cb.failure_count == 0
        assert cb.state == "closed"
        assert cb.last_failure_time is None

    def test_record_failure(self):
        """Test recording failures."""
        cb = CircuitBreaker(threshold=2, reset_timeout=10)
        
        # First failure
        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.state == "closed"
        assert cb.last_failure_time is not None
        
        # Second failure (should open circuit)
        cb.record_failure()
        assert cb.failure_count == 2
        assert cb.state == "open"
        assert cb.last_failure_time is not None

    def test_record_success(self):
        """Test recording success."""
        cb = CircuitBreaker(threshold=2, reset_timeout=10)
        
        # Record some failures
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.failure_count == 2
        
        # Record success
        cb.record_success()
        assert cb.state == "closed"
        assert cb.failure_count == 0

    def test_is_open(self):
        """Test circuit breaker state."""
        cb = CircuitBreaker(threshold=2, reset_timeout=1)  # Short timeout for testing
        
        # Initially closed
        assert not cb.is_open()
        
        # Record failures to open circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()
        
        # Wait for reset
        import time
        time.sleep(1.1)  # Slightly longer than reset_timeout
        
        # Should be closed again
        assert not cb.is_open()

    def test_reset(self):
        """Test manual reset."""
        cb = CircuitBreaker(threshold=2, reset_timeout=10)
        
        # Record failures
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.failure_count == 2
        
        # Reset
        cb.reset()
        assert cb.state == "closed"
        assert cb.failure_count == 0

    def test_get_reset_timeout_with_jitter(self):
        """Test reset timeout calculation with jitter."""
        cb = CircuitBreaker(threshold=2, reset_timeout=10, jitter=0.2)
        
        # Test multiple times to ensure jitter is within bounds
        for _ in range(100):
            timeout = cb.get_reset_timeout()
            assert 8 <= timeout <= 12  # 10 ± 2 seconds

    def test_get_reset_timeout_without_jitter(self):
        """Test reset timeout calculation without jitter."""
        cb = CircuitBreaker(threshold=2, reset_timeout=10, jitter=0.0)
        
        # Should always return exact reset_timeout
        assert cb.get_reset_timeout() == 10

    def test_circuit_breaker_lifecycle(self):
        """Test complete circuit breaker lifecycle."""
        cb = CircuitBreaker(threshold=2, reset_timeout=1)  # Short timeout for testing
        
        # Initial state
        assert not cb.is_open()
        assert cb.failure_count == 0
        
        # Record first failure
        cb.record_failure()
        assert not cb.is_open()
        assert cb.failure_count == 1
        
        # Record second failure (opens circuit)
        cb.record_failure()
        assert cb.is_open()
        assert cb.failure_count == 2
        
        # Wait for reset
        import time
        time.sleep(1.1)
        
        # Should be closed again
        assert not cb.is_open()
        assert cb.failure_count == 0
        
        # Record success
        cb.record_success()
        assert not cb.is_open()
        assert cb.failure_count == 0

    def test_zero_jitter(self):
        """Test circuit breaker with zero jitter."""
        cb = CircuitBreaker(threshold=2, reset_timeout=1, jitter=0.0)
        
        # Record failures to open circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()
        
        # Wait for exact reset time
        import time
        time.sleep(1.1)  # Slightly longer than reset_timeout
        
        # Should be closed again
        assert not cb.is_open()

    def test_maximum_jitter(self):
        """Test circuit breaker with maximum jitter."""
        cb = CircuitBreaker(threshold=2, reset_timeout=1, jitter=0.5)
        
        # Record failures to open circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()
        
        # Wait for maximum possible reset time
        import time
        time.sleep(1.6)  # Slightly longer than reset_timeout * 2
        
        # Should be closed again
        assert not cb.is_open() 