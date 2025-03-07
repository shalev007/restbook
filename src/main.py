import click
import requests
import json
import sys
from src.models.session.session_store import SessionStore
from src.models.playbook.playbook import Playbook

# Instantiate the session store (this could be injected for tests)
session_store = SessionStore()

@click.group()
def cli():
    """RestBook CLI Tool: Declarative API interactions."""
    pass

@cli.group()
def session():
    """Manage API sessions (create, list, update, delete)."""
    pass

@session.command()
@click.argument("name")
@click.option("--base-url", prompt="Base URL", help="The API base URL.")
@click.option("--token", help="Authentication token for the API.", default=None)
def create(name, base_url, token):
    """Create a new session."""
    try:
        new_session = session_store.create_session(name, base_url, token)
        click.echo(f"Session '{name}' created successfully:\n{new_session.to_dict()}")
    except ValueError as err:
        click.echo(str(err), err=True)

@session.command(name="list")
def list_sessions():
    """List all available sessions."""
    sessions = session_store.list_sessions()
    if not sessions:
        click.echo("No sessions found.")
    else:
        for session in sessions.values():
            click.echo(f"{session.to_dict()}")

@session.command()
@click.argument("name")
@click.option("--base-url", help="New API base URL.", default=None)
@click.option("--token", help="New authentication token.", default=None)
def update(name, base_url, token):
    """Update an existing session."""
    try:
        updated_session = session_store.update_session(name, base_url, token)
        click.echo(f"Session '{name}' updated successfully:\n{updated_session.to_dict()}")
    except ValueError as err:
        click.echo(str(err), err=True)

@session.command()
@click.argument("name")
def delete(name):
    """Delete an existing session."""
    try:
        session_store.delete_session(name)
        click.echo(f"Session '{name}' deleted successfully.")
    except ValueError as err:
        click.echo(str(err), err=True)

@cli.command()
@click.argument("session_name")
@click.argument("method", type=click.Choice(['GET', 'POST', 'PUT', 'DELETE', 'PATCH']))
@click.argument("endpoint")
@click.option("--data", help="JSON data to send with the request")
@click.option("--headers", help="Additional headers in JSON format")
def request(session_name, method, endpoint, data, headers):
    """Make an HTTP request using a specified session."""
    try:
        # Get the session
        sessions = session_store.list_sessions()
        if session_name not in sessions:
            raise ValueError(f"Session '{session_name}' does not exist.")
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
                raise ValueError("Headers must be in valid JSON format")

        # Prepare data
        request_data = None
        if data:
            try:
                request_data = json.loads(data)
            except json.JSONDecodeError:
                raise ValueError("Data must be in valid JSON format")

        # Make the request
        response = requests.request(
            method=method,
            url=url,
            headers=request_headers,
            json=request_data
        )

        # Print response
        click.echo(f"Status: {response.status_code}")
        click.echo("Headers:")
        for key, value in response.headers.items():
            click.echo(f"  {key}: {value}")
        click.echo("\nBody:")
        try:
            click.echo(json.dumps(response.json(), indent=2))
        except:
            click.echo(response.text)

    except ValueError as err:
        click.echo(str(err), err=True)
    except requests.exceptions.RequestException as err:
        click.echo(f"Request failed: {str(err)}", err=True)

@cli.command()
@click.argument('playbook_file', type=click.File('r'), required=False)
def run(playbook_file):
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
        playbook = Playbook.from_yaml(content, logger=click.echo)
        playbook.execute(session_store)

    except ValueError as err:
        click.echo(str(err), err=True)
    except requests.exceptions.RequestException as err:
        click.echo(f"Request failed: {str(err)}", err=True)

def main():
    cli()

if __name__ == '__main__':
    main()
