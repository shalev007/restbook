import json
import sys
from .base import BaseLogger


class JsonLogger(BaseLogger):
    """Logger that outputs JSON for machine parsing."""
    
    def log_step(self, step_number: int, method: str, endpoint: str):
        print(json.dumps({
            "type": "step",
            "step_number": step_number,
            "method": method,
            "endpoint": endpoint
        }))

    def log_status(self, status_code: int):
        print(json.dumps({
            "type": "status",
            "code": status_code
        }))

    def log_headers(self, headers: dict):
        print(json.dumps({
            "type": "headers",
            "headers": headers
        }))

    def log_body(self, body: str):
        print(json.dumps({
            "type": "body",
            "content": body
        }))

    def log_error(self, message: str):
        print(json.dumps({
            "type": "error",
            "message": message
        }), file=sys.stderr)

    def log_info(self, message: str):
        print(json.dumps({
            "type": "info",
            "message": message
        })) 