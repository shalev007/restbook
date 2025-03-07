from abc import ABC, abstractmethod
from typing import Optional, Type
import json
import click
import sys


class BaseLogger(ABC):
    """Abstract base class for loggers."""
    
    @abstractmethod
    def log_step(self, step_number: int, method: str, endpoint: str):
        """Log a step execution."""
        pass

    @abstractmethod
    def log_status(self, status_code: int):
        """Log a response status code."""
        pass

    @abstractmethod
    def log_headers(self, headers: dict):
        """Log response headers."""
        pass

    @abstractmethod
    def log_body(self, body: str):
        """Log response body."""
        pass

    @abstractmethod
    def log_error(self, message: str):
        """Log an error message."""
        pass

    @abstractmethod
    def log_info(self, message: str):
        """Log an info message."""
        pass


class ColorfulLogger(BaseLogger):
    """Logger that outputs colorful text for CLI usage."""
    
    def log_step(self, step_number: int, method: str, endpoint: str):
        click.echo(click.style(f"\nStep {step_number}", fg="cyan", bold=True))
        click.echo(click.style(f"Method: {method}", fg="white"))
        click.echo(click.style(f"Endpoint: {endpoint}", fg="white"))

    def log_status(self, status_code: int):
        color = "green" if str(status_code).startswith("2") else "red" if str(status_code).startswith("4") else "yellow"
        click.echo(click.style(f"Status: {status_code}", fg=color, bold=True))

    def log_headers(self, headers: dict):
        click.echo(click.style("Headers:", fg="blue", bold=True))
        for key, value in headers.items():
            click.echo(click.style(f"  {key}: {value}", fg="white"))

    def log_body(self, body: str):
        click.echo(click.style("\nBody:", fg="white", bold=True))
        click.echo(body)

    def log_error(self, message: str):
        click.echo(click.style(message, fg="red", bold=True), err=True)

    def log_info(self, message: str):
        click.echo(message)


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


def create_logger(output_type: str) -> BaseLogger:
    """Factory function to create the appropriate logger."""
    loggers: dict[str, Type[BaseLogger]] = {
        "colorful": ColorfulLogger,
        "plain": PlainLogger,
        "json": JsonLogger
    }
    
    if output_type.lower() not in loggers:
        raise ValueError(f"Invalid output type: {output_type}. Must be one of: {', '.join(loggers.keys())}")
    
    return loggers[output_type.lower()]() 