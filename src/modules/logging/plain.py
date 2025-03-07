import sys
from .base import BaseLogger


class PlainLogger(BaseLogger):
    """Logger that outputs plain text, suitable for CI/file output."""
    
    def log_step(self, step_number: int, method: str, endpoint: str):
        print(f"\nStep {step_number}")
        print(f"Method: {method}")
        print(f"Endpoint: {endpoint}")

    def log_status(self, status_code: int):
        print(f"Status: {status_code}")

    def log_headers(self, headers: dict):
        print("Headers:")
        for key, value in headers.items():
            print(f"  {key}: {value}")

    def log_body(self, body: str):
        print("\nBody:")
        print(body)

    def log_error(self, message: str):
        print(message, file=sys.stderr)

    def log_info(self, message: str):
        print(message) 