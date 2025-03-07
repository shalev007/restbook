import click
import requests
import json
import sys
from src.modules.session.session_store import SessionStore
from src.modules.playbook.playbook import Playbook
from src.modules.logging import create_logger, BaseLogger

# Instantiate the session store (this could be injected for tests)
session_store = SessionStore()

class RestbookContext:
    """Context object to store CLI state."""
    def __init__(self):
        self.logger = None

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

@cli.group()
def session():
    """Manage API sessions (create, list, update, delete)."""
    pass

@session.command()
@click.argument("name")
@click.option("--base-url", prompt="Base URL", help="The API base URL.")
@click.option("--token", help="Authentication token for the API.", default=None)
@pass_context
def create(ctx, name, base_url, token):
    """Create a new session."""
    try:
        new_session = session_store.create_session(name, base_url, token)
        ctx.logger.log_info(f"Session '{name}' created successfully:")
        ctx.logger.log_info(json.dumps(new_session.to_dict(), indent=2))
    except ValueError as err:
        ctx.logger.log_error(str(err))

@session.command(name="list")
@pass_context
def list_sessions(ctx):
    """List all available sessions."""
    sessions = session_store.list_sessions()
    if not sessions:
        ctx.logger.log_info("No sessions found.")
    else:
        for session in sessions.values():
            ctx.logger.log_info(json.dumps(session.to_dict(), indent=2))

@session.command()
@click.argument("name")
@click.option("--base-url", help="New API base URL.", default=None)
@click.option("--token", help="New authentication token.", default=None)
@pass_context
def update(ctx, name, base_url, token):
    """Update an existing session."""
    try:
        updated_session = session_store.update_session(name, base_url, token)
        ctx.logger.log_info(f"Session '{name}' updated successfully:")
        ctx.logger.log_info(json.dumps(updated_session.to_dict(), indent=2))
    except ValueError as err:
        ctx.logger.log_error(str(err))

@session.command()
@click.argument("name")
@pass_context
def delete(ctx, name):
    """Delete an existing session."""
    try:
        session_store.delete_session(name)
        ctx.logger.log_info(f"Session '{name}' deleted successfully.")
    except ValueError as err:
        ctx.logger.log_error(str(err))

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
        sessions = session_store.list_sessions()
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

@cli.command()
@click.argument('playbook_file', type=click.File('r'), required=False)
@pass_context
def run(ctx, playbook_file):
    """Execute a YAML playbook from a file or stdin.
    
    If no file is specified, reads from stdin.
    """
    try:
        # Read from file or stdin
        if playbook_file is None:
            if sys.stdin.isatty():
                raise click.UsageError("Please provide a playbook file or pipe YAML content")
            content = sys.stdin.read()
        else:
            content = playbook_file.read()

        # Parse and execute the playbook with logging
        playbook = Playbook.from_yaml(content, logger=ctx.logger)
        playbook.execute(session_store)

    except ValueError as err:
        ctx.logger.log_error(str(err))
    except requests.exceptions.RequestException as err:
        ctx.logger.log_error(f"Request failed: {str(err)}")

def main():
    cli()

if __name__ == '__main__':
    main()
