from datetime import datetime, timedelta, UTC
from typing import Optional
import random

class CircuitBreaker:
    def __init__(self, threshold: int, reset_timeout: int, jitter: float = 0.0):
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.jitter = jitter
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"
    
    def get_reset_timeout(self) -> float:
        if self.jitter:
            return self.reset_timeout + random.uniform(0, self.jitter)
        return self.reset_timeout

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)
        if self.failure_count >= self.threshold:
            self.state = "open"

    def record_success(self):
        self.failure_count = 0
        self.state = "closed"

    def is_open(self) -> bool:
        if self.state == "open" and self.last_failure_time:
            # Calculate jittered reset timeout
            jittered_timeout = self.get_reset_timeout()
            if datetime.now(UTC) - self.last_failure_time > timedelta(seconds=jittered_timeout):
                self.reset()
                return False
            return True
        return False

    def reset(self):
        self.failure_count = 0
        self.state = "closed"
