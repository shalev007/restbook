import click
import requests
import json
import sys
from src.modules.session.session_store import SessionStore
from src.modules.session.commands import create_session_commands
from src.modules.playbook.commands import create_playbook_commands
from src.modules.logging import create_logger, BaseLogger


class RestbookContext:
    """Context object to store CLI state."""
    def __init__(self):
        self.logger = None
        self.session_store = SessionStore()

pass_context = click.make_pass_decorator(RestbookContext, ensure=True)

@click.group()
@click.option('--output', '-o',
              type=click.Choice(['colorful', 'plain', 'json']),
              default='colorful',
              help='Output format (colorful for CLI, plain for CI/file, json for machine parsing)',
              envvar='RESTBOOK_OUTPUT')
@pass_context
def cli(ctx, output):
    """RestBook CLI Tool: Declarative API interactions."""
    ctx.logger = create_logger(output)

# Add commands
cli.add_command(create_session_commands())
cli.add_command(create_playbook_commands())

@cli.command()
@click.argument("session_name")
@click.argument("method", type=click.Choice(['GET', 'POST', 'PUT', 'DELETE', 'PATCH']))
@click.argument("endpoint")
@click.option("--data", help="JSON data to send with the request")
@click.option("--headers", help="Additional headers in JSON format")
@pass_context
def request(ctx, session_name, method, endpoint, data, headers):
    """Make an HTTP request using a specified session."""
    try:
        # Get the session
        sessions = ctx.session_store.list_sessions()
        if session_name not in sessions:
            error_msg = f"Session '{session_name}' does not exist."
            ctx.logger.log_error(error_msg)
            raise ValueError(error_msg)
        session = sessions[session_name]

        # Prepare the request
        url = f"{session.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Prepare headers
        request_headers = {}
        if session.token:
            request_headers['Authorization'] = f"Bearer {session.token}"
        if headers:
            try:
                request_headers.update(json.loads(headers))
            except json.JSONDecodeError:
                error_msg = "Headers must be in valid JSON format"
                ctx.logger.log_error(error_msg)
                raise ValueError(error_msg)

        # Prepare data
        request_data = None
        if data:
            try:
                request_data = json.loads(data)
            except json.JSONDecodeError:
                error_msg = "Data must be in valid JSON format"
                ctx.logger.log_error(error_msg)
                raise ValueError(error_msg)

        # Make the request
        response = requests.request(
            method=method,
            url=url,
            headers=request_headers,
            json=request_data
        )

        # Log response
        ctx.logger.log_status(response.status_code)
        ctx.logger.log_headers(dict(response.headers))
        try:
            body = json.dumps(response.json(), indent=2)
        except:
            body = response.text
        ctx.logger.log_body(body)

    except ValueError as err:
        ctx.logger.log_error(str(err))
    except requests.exceptions.RequestException as err:
        ctx.logger.log_error(f"Request failed: {str(err)}")

def main():
    cli()

if __name__ == '__main__':
    main()
