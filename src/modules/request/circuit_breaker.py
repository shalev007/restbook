from datetime import datetime, timedelta, UTC
from typing import Optional

class CircuitBreaker:
    def __init__(self, threshold: int, reset_timeout: int):
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"

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
            if datetime.now(UTC) - self.last_failure_time > timedelta(seconds=self.reset_timeout):
                self.reset()
                return False
            return True
        return False

    def reset(self):
        self.failure_count = 0
        self.state = "closed"
