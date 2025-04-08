import click
from .base import BaseLogger
import sys


class ColorfulLogger(BaseLogger):
    """Logger that outputs colorful text for CLI usage."""
    
    def __init__(self, log_level: str = "INFO"):
        super().__init__()
        # Configure loguru for colored output
        self.logger.configure(
            handlers=[{
                "sink": sys.stdout,
                "colorize": True,
                "format": "<cyan>{time:YYYY-MM-DD HH:mm:ss.SSS}</cyan> | "
                         "<level>{level: <8}</level> | "
                         "<white>{message}</white>",
                "level": log_level
            }]
        )
    
    def log_step(self, step_number: int, method: str, endpoint: str):
        self.logger.info(click.style(f"Step {step_number}", fg="cyan", bold=True))
        self.logger.info(click.style(f"Method: {method}", fg="white"))
        self.logger.info(click.style(f"Endpoint: {endpoint}", fg="white"))

    def log_status(self, status_code: int):
        if status_code >= 500:
            color = "red"
        elif status_code >= 400:
            color = "yellow"
        elif status_code >= 300:
            color = "blue"
        elif status_code >= 200:
            color = "green"
        else:
            color = "white"
            
        self.logger.info(click.style(f"Status: {status_code}", fg=color, bold=True))

    def log_headers(self, headers: dict):
        self.logger.info(click.style("Headers:", fg="blue", bold=True))
        for key, value in headers.items():
            self.logger.info(click.style(f"  {key}: {value}", fg="white"))

    def log_body(self, body: str):
        self.logger.info(click.style("\nBody:", fg="magenta", bold=True))
        self.logger.info(click.style(body, fg="white"))

    def log_error(self, message: str):
        self.logger.error(click.style(message, fg="red", bold=True))

    def log_warning(self, message: str):
        self.logger.warning(click.style(message, fg="yellow", bold=True))

    def log_info(self, message: str):
        self.logger.info(click.style(message, fg="white"))

    def log_debug(self, message: str):
        self.logger.debug(click.style(message, fg="blue")) 