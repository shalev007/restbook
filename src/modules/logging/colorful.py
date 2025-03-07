import click
from .base import BaseLogger


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